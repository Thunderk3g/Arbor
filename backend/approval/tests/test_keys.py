from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from r2pip_approval.keys import (
    generate_keypair,
    load_private_key_pem,
    load_public_key_pem,
    serialize_private_key_pem,
    serialize_public_key_pem,
)


def test_generate_keypair_types():
    private_key, public_key = generate_keypair()
    assert isinstance(private_key, Ed25519PrivateKey)
    assert isinstance(public_key, Ed25519PublicKey)


def test_private_key_pem_roundtrip():
    private_key, _ = generate_keypair()
    pem = serialize_private_key_pem(private_key)
    assert b"BEGIN PRIVATE KEY" in pem
    loaded = load_private_key_pem(pem)
    assert serialize_private_key_pem(loaded) == pem


def test_public_key_pem_roundtrip():
    _, public_key = generate_keypair()
    pem = serialize_public_key_pem(public_key)
    assert b"BEGIN PUBLIC KEY" in pem
    loaded = load_public_key_pem(pem)
    assert serialize_public_key_pem(loaded) == pem
