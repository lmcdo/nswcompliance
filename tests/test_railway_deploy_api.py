"""scripts/railway_deploy_api.py: every merge to main reaches the API service.

On 2026-10-28/29 Railway stopped deploying the `nswcompliance` service while
its other services deployed; two merged PRs sat undeployed. These pin the three
paths: Railway already deploying (watch, never deploy twice), Railway not
deploying (start it), and a failed deploy (exit 1 so the job goes red).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import railway_deploy_api as rd  # noqa: E402

SHA = "d3350f17299fb4306cc918d26a10a548c008b108"


def _run(monkeypatch, deployments, statuses):
    calls = []

    def fake_gql(token, query, variables=None):
        calls.append(query)
        if "deployments(" in query:
            return {"deployments": {"edges": [{"node": d} for d in deployments]}}
        if "serviceInstanceDeployV2" in query:
            return {"serviceInstanceDeployV2": "new-dep"}
        return {"deployment": {"status": statuses.pop(0)}}

    monkeypatch.setattr(rd, "gql", fake_gql)
    monkeypatch.setattr(rd.time, "sleep", lambda s: None)
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("GITHUB_SHA", SHA)
    return rd.main(), calls


def test_an_existing_deployment_is_watched_not_duplicated(monkeypatch):
    code, calls = _run(monkeypatch, [{"id": "d1", "status": "BUILDING", "meta": {"commitHash": SHA}}],
                       ["DEPLOYING", "SUCCESS"])
    assert code == 0
    assert not any("serviceInstanceDeployV2" in q for q in calls)


def test_a_missing_deployment_is_started(monkeypatch):
    code, calls = _run(monkeypatch, [{"id": "old", "status": "SKIPPED", "meta": {"commitHash": SHA}}],
                       ["SUCCESS"])
    assert code == 0
    assert any("serviceInstanceDeployV2" in q for q in calls)


def test_a_failed_deploy_fails_the_job(monkeypatch):
    code, _ = _run(monkeypatch, [], ["BUILDING", "FAILED"])
    assert code == 1


def test_no_token_fails_rather_than_passing(monkeypatch):
    monkeypatch.delenv("RAILWAY_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_SHA", SHA)
    assert rd.main() == 1
