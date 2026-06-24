"""FastAPI surface tests for the platform service."""

from fastapi.testclient import TestClient

from r2pip_platform.app import create_app


def client() -> TestClient:
    return TestClient(create_app())


class TestHealthAndTools:
    def test_health(self):
        body = client().get("/health").json()
        assert body["status"] == "ok"
        assert body["tools"] == 17

    def test_tools_lists_all_families(self):
        body = client().get("/tools").json()
        families = {t["family"] for t in body["tools"]}
        assert families == {"perception", "computation", "action", "memory"}
        deploy = next(t for t in body["tools"] if t["name"] == "deploy.release")
        assert deploy["requires_approval"] is True


class TestRunMission:
    def test_run_mission_completes(self):
        body = client().post("/missions/run", json={}).json()
        assert body["state"]["status"] == "completed"
        assert body["chain_valid"] is True
        assert body["state"]["deployed"] is True

    def test_run_mission_custom_tenant(self):
        body = client().post("/missions/run", json={"tenant_id": "beta-corp"}).json()
        assert body["state"]["spec"]["tenant_id"] == "beta-corp"
        assert body["state"]["status"] == "completed"
