import jwt
import pytest

from r2pip_approval.keys import generate_keypair
from r2pip_approval.models import ApprovalDecision, ApprovalRequest
from r2pip_approval.service import ApprovalService

from approval_helpers import make_request


def approve(approver_id="alice", **kwargs):
    return ApprovalDecision(approver_id=approver_id, decision="approve", **kwargs)


def reject(approver_id="alice", **kwargs):
    return ApprovalDecision(approver_id=approver_id, decision="reject", **kwargs)


class TestHappyPath:
    def test_create_approve_verify(self, service):
        request = make_request(service)
        assert request.status == "pending"

        outcome = service.decide(request.id, approve("alice"))
        assert outcome.request.status == "approved"
        assert outcome.token is not None

        result = service.verify(outcome.token, request.params_hash)
        assert result.valid is True
        assert result.reason is None
        assert result.approver == "alice"
        assert result.checkpoint == "H5"

    def test_token_claims(self, service, keypair):
        _, public_key = keypair
        request = make_request(service)
        outcome = service.decide(request.id, approve("alice"))
        claims = jwt.decode(outcome.token, public_key, algorithms=["EdDSA"])
        assert claims["params_hash"] == request.params_hash
        assert claims["action_type"] == "deploy"
        assert claims["tenant_id"] == "tenant-1"
        assert claims["single_use"] is True
        assert claims["jti"]
        assert claims["exp"] > claims["iat"]


class TestReplay:
    def test_second_verify_fails(self, service):
        request = make_request(service)
        token = service.decide(request.id, approve()).token

        assert service.verify(token, request.params_hash).valid is True
        result = service.verify(token, request.params_hash)
        assert result.valid is False
        assert result.reason == "token_already_used"


class TestParamsBinding:
    def test_different_params_hash_fails(self, service):
        request = make_request(service, params_hash="a" * 64)
        token = service.decide(request.id, approve()).token

        result = service.verify(token, "b" * 64)
        assert result.valid is False
        assert result.reason == "params_mismatch"

    def test_mismatch_does_not_consume_token(self, service):
        request = make_request(service)
        token = service.decide(request.id, approve()).token

        assert service.verify(token, "b" * 64).valid is False
        assert service.verify(token, request.params_hash).valid is True


class TestTampering:
    def test_flipped_character_fails(self, service):
        request = make_request(service)
        token = service.decide(request.id, approve()).token

        # Flip a character in the PAYLOAD segment, not the signature tail.
        # The last base64url char of an Ed25519 signature encodes only 2
        # significant bits (the rest are discarded padding), so flipping it
        # can decode to the identical signature and verify legitimately -> flaky.
        # Changing the signed header.payload string makes the signature
        # deterministically invalid.
        header, payload, signature = token.split(".")
        idx = len(payload) // 2
        flipped = "A" if payload[idx] != "A" else "B"
        tampered = ".".join([header, payload[:idx] + flipped + payload[idx + 1 :], signature])

        result = service.verify(tampered, request.params_hash)
        assert result.valid is False
        assert result.reason == "invalid_token"

    def test_token_signed_by_other_key_fails(self, service):
        other_private, _ = generate_keypair()
        rogue = ApprovalService(other_private)
        request = make_request(rogue)
        token = rogue.decide(request.id, approve("mallory")).token

        result = service.verify(token, request.params_hash)
        assert result.valid is False
        assert result.reason == "invalid_token"


class TestExpiry:
    def test_expired_token_fails(self, keypair):
        private_key, _ = keypair
        service = ApprovalService(private_key, token_ttl_seconds=-1)
        request = make_request(service)
        token = service.decide(request.id, approve()).token

        result = service.verify(token, request.params_hash)
        assert result.valid is False
        assert result.reason == "expired"


class TestDestructive:
    def test_create_without_consequence_raises(self, service):
        with pytest.raises(ValueError):
            make_request(service, destructive=True, required_consequence=None)

    def test_model_validation_rejects_missing_consequence(self):
        with pytest.raises(ValueError):
            ApprovalRequest(
                id="x",
                tenant_id="t",
                checkpoint="H6",
                action_type="delete_tenant",
                subject_id="t-2",
                params_hash="c" * 64,
                risk_score=0.9,
                destructive=True,
            )

    def test_wrong_typed_consequence_rejected(self, service):
        request = make_request(
            service,
            destructive=True,
            required_consequence="delete tenant t-2 permanently",
        )
        with pytest.raises(ValueError):
            service.decide(
                request.id, approve(typed_consequence="delete tenant t-2")
            )
        assert service.get_request(request.id).status == "rejected"

    def test_exact_typed_consequence_succeeds(self, service):
        request = make_request(
            service,
            destructive=True,
            required_consequence="delete tenant t-2 permanently",
        )
        outcome = service.decide(
            request.id, approve(typed_consequence="delete tenant t-2 permanently")
        )
        assert outcome.request.status == "approved"
        assert outcome.token is not None


class TestDualControl:
    def test_first_approval_pending_no_token(self, service):
        request = make_request(service, dual_control=True)
        outcome = service.decide(request.id, approve("alice"))
        assert outcome.request.status == "pending"
        assert outcome.token is None

    def test_same_approver_twice_does_not_count(self, service):
        request = make_request(service, dual_control=True)
        service.decide(request.id, approve("alice"))
        with pytest.raises(ValueError):
            service.decide(request.id, approve("alice"))
        current = service.get_request(request.id)
        assert current.status == "pending"
        assert len(current.approvals) == 1

    def test_second_distinct_approver_issues_token(self, service):
        request = make_request(service, dual_control=True)
        assert service.decide(request.id, approve("alice")).token is None
        outcome = service.decide(request.id, approve("bob"))
        assert outcome.request.status == "approved"
        assert outcome.token is not None

        result = service.verify(outcome.token, request.params_hash)
        assert result.valid is True
        assert result.approver == "alice,bob"


class TestReject:
    def test_rejected_cannot_be_approved(self, service):
        request = make_request(service)
        outcome = service.decide(request.id, reject("alice", comment="too risky"))
        assert outcome.request.status == "rejected"
        assert outcome.token is None

        with pytest.raises(ValueError):
            service.decide(request.id, approve("bob"))

    def test_approved_cannot_be_decided_again(self, service):
        request = make_request(service)
        service.decide(request.id, approve("alice"))
        with pytest.raises(ValueError):
            service.decide(request.id, approve("bob"))

    def test_unknown_request_raises(self, service):
        with pytest.raises(KeyError):
            service.decide("missing-id", approve())
