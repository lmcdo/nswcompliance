"""Make sure the API service (Railway `nswcompliance`) deploys every merge to main.

Why: on 2026-10-28/29 Railway stopped creating deployments for this one service
after 21:49, while the other eight services in the project deployed the same
commits. Two merged flood PRs (#1545, #1548) sat undeployed for hours with no
alarm. The trigger settings were correct (branch main, watch paths include
services/**, wait-for-CI off), so the cause is on Railway's side.

What this does (run by .github/workflows/deploy-api.yml on push to main):
  1. If Railway already created a deployment for this commit, watch it.
  2. Otherwise ask Railway to deploy this commit (serviceInstanceDeployV2).
  3. Poll until SUCCESS; exit 1 on FAILED/CRASHED/REMOVED/timeout so the
     GitHub job goes red instead of the API silently serving old code.

Env: RAILWAY_TOKEN (account token, repo secret), GITHUB_SHA.
prior-art-checked: scripts/check_railway_jobs_ran.py and check_railway_cron_drift.py
only READ Railway state; nothing triggered a deploy.
"""
from __future__ import annotations

import os
import sys
import time

import requests

API = "https://backboard.railway.app/graphql/v2"
PROJECT = "bbf07e70-b9ce-4776-9523-090be5b84753"
SERVICE = "07f8bf7a-0f65-4f6a-b270-4a9fe21a2703"      # nswcompliance (the Python API)
ENVIRONMENT = "8bde9fcd-b5f0-4cd8-8ca2-e405995f112f"  # production
DONE = {"SUCCESS"}
BAD = {"FAILED", "CRASHED", "REMOVED"}
TIMEOUT_S = 25 * 60
GRACE_S = 60


def gql(token: str, query: str, variables: dict | None = None) -> dict:
    r = requests.post(API, json={"query": query, "variables": variables or {}},
                      headers={"Authorization": f"Bearer {token}"}, timeout=30)
    r.raise_for_status()
    body = r.json()
    if body.get("errors"):
        raise RuntimeError(f"Railway API error: {body.get('errors')}")
    return body.get("data") or {}


def existing_deployment(token: str, sha: str) -> dict | None:
    """A deployment Railway already made for this commit, ignoring SKIPPED/REMOVED ones."""
    data = gql(token, """query($p: String!, $s: String!, $e: String!) {
        deployments(first: 20, input: {projectId: $p, serviceId: $s, environmentId: $e}) {
          edges { node { id status meta } } } }""", {"p": PROJECT, "s": SERVICE, "e": ENVIRONMENT})
    for edge in (data.get("deployments") or {}).get("edges") or []:
        node = edge.get("node") or {}
        meta = node.get("meta") or {}
        # A failed/crashed/skipped/removed attempt is not "already deploying": a re-run retries.
        if meta.get("commitHash") == sha and node.get("status") not in ("SKIPPED", "REMOVED", "FAILED", "CRASHED"):
            return node
    return None


def status_of(token: str, deployment_id: str) -> str:
    data = gql(token, "query($id: String!) { deployment(id: $id) { status } }", {"id": deployment_id})
    return ((data.get("deployment") or {}).get("status")) or "UNKNOWN"


def main() -> int:
    token = os.environ.get("RAILWAY_TOKEN")
    sha = os.environ.get("GITHUB_SHA")
    if not token or not sha:
        print("DEPLOY-API: RAILWAY_TOKEN and GITHUB_SHA are required")
        return 1
    # Give Railway's own trigger a minute to record its deployment first, so
    # the lookup below does not race it into a second build.
    time.sleep(GRACE_S)
    found = existing_deployment(token, sha)
    if found:
        dep_id = found.get("id")
        print(f"DEPLOY-API: Railway already deploying {sha[:8]} ({dep_id}, {found.get('status')})")
    else:
        data = gql(token, """mutation($s: String!, $e: String!, $c: String!) {
            serviceInstanceDeployV2(serviceId: $s, environmentId: $e, commitSha: $c) }""",
                   {"s": SERVICE, "e": ENVIRONMENT, "c": sha})
        dep_id = data.get("serviceInstanceDeployV2")
        print(f"DEPLOY-API: Railway had not deployed {sha[:8]}; started {dep_id}")
    if not dep_id:
        print("DEPLOY-API: no deployment id returned")
        return 1
    start = time.time()
    st = "UNKNOWN"
    while time.time() - start < TIMEOUT_S:
        st = status_of(token, dep_id)
        if st in DONE:
            print(f"DEPLOY-API: {sha[:8]} deployed ({dep_id})")
            return 0
        if st in BAD:
            print(f"DEPLOY-API: deployment {dep_id} ended {st}")
            return 1
        time.sleep(20)
    print(f"DEPLOY-API: still {st} after {TIMEOUT_S // 60} min ({dep_id})")
    return 1


if __name__ == "__main__":
    sys.exit(main())
