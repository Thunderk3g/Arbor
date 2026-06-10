def make_request(service, **overrides):
    params = dict(
        tenant_id="tenant-1",
        checkpoint="H5",
        action_type="deploy",
        subject_id="svc-payments",
        params_hash="a" * 64,
        risk_score=0.4,
        evidence_bundle={"revision": "rev-A"},
    )
    params.update(overrides)
    return service.create_request(**params)
