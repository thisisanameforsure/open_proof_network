"""F26-Q17 (the owner's ruling, 2026-10-12): the review notice runs nightly from a workflow that
invokes the deployed function with ``{"opn_task": "review-notice"}``. The role it assumes may do
that and nothing else, and only from this repository's main branch; the workflow pins its actions
and asks for no secret, so the App key and the store never leave AWS.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from test_finding_api_stack_hardening import template

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "review-notice.yml"


def notice_role() -> dict[str, Any]:
    role = template()["Resources"]["NoticeRole"]
    assert role["Type"] == "AWS::IAM::Role"
    return dict(role["Properties"])


def test_the_notice_role_may_only_invoke_the_function() -> None:
    (policy,) = notice_role()["Policies"]
    (statement,) = policy["PolicyDocument"]["Statement"]
    assert statement["Effect"] == "Allow"
    assert statement["Action"] in (["lambda:InvokeFunction"], "lambda:InvokeFunction")
    assert statement["Resource"] == {"!GetAtt": "Function.Arn"}


def test_the_notice_role_is_trusted_exactly_as_the_deploy_role() -> None:
    resources = template()["Resources"]
    deploy = resources["DeployRole"]["Properties"]["AssumeRolePolicyDocument"]
    notice = notice_role()["AssumeRolePolicyDocument"]
    assert notice == deploy  # the same OIDC provider, audience and repo-and-branch subject


def test_the_template_outputs_the_notice_role() -> None:
    outputs = template()["Outputs"]
    assert outputs["NoticeRoleArn"]["Value"] == {"!GetAtt": "NoticeRole.Arn"}


def test_the_workflow_runs_nightly_and_on_dispatch_with_no_secret() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    doc = yaml.safe_load(text)
    on = doc[True] if True in doc else doc["on"]  # yaml reads a bare `on` as True
    assert set(on) == {"schedule", "workflow_dispatch"}
    assert "secrets." not in text, "the notice needs no secret: the function holds the key"
    assert doc["permissions"] == {"id-token": "write", "contents": "read"}
    steps = doc["jobs"]["notice"]["steps"]
    uses = [s["uses"] for s in steps if "uses" in s]
    for u in uses:
        ref = u.split("@", 1)[1]
        assert len(ref.split()[0]) == 40, u  # a full commit, as the action-pin scan requires
    assert any("vars.OPN_API_NOTICE_ROLE_ARN" in str(s.get("with", {})) for s in steps)
    run = "\n".join(str(s.get("run", "")) for s in steps)
    assert "aws lambda invoke" in run and '"opn_task": "review-notice"' in run


def test_the_workflow_counts_posts_by_the_field_the_notice_emits() -> None:
    """The summary line reads each outcome's ``posted`` (review_notice.outcome), never a field the
    notice does not write."""
    from opn_api import review_notice  # noqa: PLC0415

    sample = review_notice.outcome("t", review_notice.POSTED, ["q-1"])
    assert sample["posted"] is True
    text = WORKFLOW.read_text(encoding="utf-8")
    assert 'o.get("posted") is True' in text and 'o.get("outcome")' not in text
