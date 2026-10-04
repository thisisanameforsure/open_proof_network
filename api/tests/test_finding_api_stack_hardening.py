"""F05-T22: the api stack carries limits, alarms and protection (audit 2026-10-04).

The audit read ``api/infra/api.cfn.yaml`` and found the service's only defences against a flood or
a runaway bill were the per-identity rate limits inside the function: the HTTP API stage had no
throttling, the function no reserved concurrency, nothing alarmed, no budget watched the account,
no table was kept if the stack replaced or deleted it, and the claims table alone had no
point-in-time recovery. Each test here reads the template itself, so a later edit that drops a
guard turns one of them red.

The template is parsed with a SafeLoader that turns CloudFormation's ``!`` tags into plain
``{"!Tag": value}`` mappings, so the assertions see the same structure CloudFormation does.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "api" / "infra" / "api.cfn.yaml"
SERVICE = ROOT / "api" / "opn_api"


class CfnLoader(yaml.SafeLoader):  # type: ignore[misc]  # yaml ships no stubs
    """SafeLoader that reads ``!Ref x`` as ``{"!Ref": "x"}`` (and so on for every tag)."""


def _tagged(loader: yaml.SafeLoader, suffix: str, node: yaml.Node) -> dict[str, Any]:
    value: Any
    if isinstance(node, yaml.ScalarNode):
        value = loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        value = loader.construct_sequence(node, deep=True)
    else:
        assert isinstance(node, yaml.MappingNode)
        value = loader.construct_mapping(node, deep=True)
    return {f"!{suffix}": value}


CfnLoader.add_multi_constructor("!", _tagged)


def template() -> dict[str, Any]:
    doc = yaml.load(TEMPLATE.read_text(encoding="utf-8"), Loader=CfnLoader)  # noqa: S506
    assert isinstance(doc, dict)
    return doc


def resources(kind: str) -> dict[str, dict[str, Any]]:
    found = {k: v for k, v in template()["Resources"].items() if v["Type"] == kind}
    assert found, f"guard: the template declares no {kind}"
    return found


def one(kind: str) -> dict[str, Any]:
    (only,) = resources(kind).values()
    return only


def test_the_stage_throttles_every_route_from_parameters() -> None:
    settings = one("AWS::ApiGatewayV2::Stage")["Properties"]["DefaultRouteSettings"]
    params = template()["Parameters"]
    for key in ("ThrottlingBurstLimit", "ThrottlingRateLimit"):
        ref = settings[key]
        assert isinstance(ref, dict) and "!Ref" in ref, key
        assert int(params[ref["!Ref"]]["Default"]) > 0, key


def test_the_function_reserves_its_concurrency_from_a_parameter() -> None:
    fn = one("AWS::Lambda::Function")["Properties"]
    ref = fn["ReservedConcurrentExecutions"]
    assert isinstance(ref, dict) and "!Ref" in ref
    assert int(template()["Parameters"][ref["!Ref"]]["Default"]) > 0


def test_the_function_sends_its_info_lines_to_cloudwatch() -> None:
    """The metric filters below match INFO lines; Lambda's plain-text default drops below WARN."""
    logging = one("AWS::Lambda::Function")["Properties"]["LoggingConfig"]
    assert logging["LogFormat"] == "JSON"
    assert logging["ApplicationLogLevel"] == "INFO"


def test_every_table_is_retained_and_recoverable() -> None:
    for name, table in resources("AWS::DynamoDB::Table").items():
        assert table.get("DeletionPolicy") == "Retain", name
        assert table.get("UpdateReplacePolicy") == "Retain", name
        pitr = table["Properties"].get("PointInTimeRecoverySpecification", {})
        assert pitr.get("PointInTimeRecoveryEnabled") is True, name


def test_alarms_go_to_one_topic_with_an_optional_email() -> None:
    doc = template()
    (topic_id,) = resources("AWS::SNS::Topic")
    sub = one("AWS::SNS::Subscription")
    assert sub["Properties"]["Protocol"] == "email"
    assert sub["Properties"]["Endpoint"] == {"!Ref": "AlarmEmail"}
    assert doc["Parameters"]["AlarmEmail"]["Default"] == ""
    assert sub.get("Condition") in doc["Conditions"]
    # A topic policy replaces SNS's default one, so it must let both publishers in.
    policy = one("AWS::SNS::TopicPolicy")["Properties"]
    principals = {s["Principal"]["Service"] for s in policy["PolicyDocument"]["Statement"]}
    assert {"budgets.amazonaws.com", "cloudwatch.amazonaws.com"} <= principals
    for alarm_id, alarm in resources("AWS::CloudWatch::Alarm").items():
        assert alarm["Properties"]["AlarmActions"] == [{"!Ref": topic_id}], alarm_id


def _alarm_on(namespace: str, metric: str) -> dict[str, Any]:
    hits = [
        a["Properties"]
        for a in resources("AWS::CloudWatch::Alarm").values()
        if a["Properties"].get("Namespace") == namespace
        and a["Properties"].get("MetricName") == metric
    ]
    assert len(hits) == 1, (namespace, metric, len(hits))
    found: dict[str, Any] = hits[0]
    return found


def test_the_api_and_the_function_are_alarmed() -> None:
    for metric in ("4xx", "5xx"):
        dims = _alarm_on("AWS/ApiGateway", metric)["Dimensions"]
        assert dims == [{"Name": "ApiId", "Value": {"!Ref": "HttpApi"}}], metric
    for metric in ("Throttles", "Errors", "Invocations"):
        dims = _alarm_on("AWS/Lambda", metric)["Dimensions"]
        assert dims == [{"Name": "FunctionName", "Value": {"!Ref": "Function"}}], metric


def _service_info_lines() -> str:
    return "\n".join(p.read_text("utf-8") for p in SERVICE.rglob("*.py"))


def test_the_metric_filters_match_lines_the_service_emits() -> None:
    """Read the filters against the service's own format strings, not from memory."""
    filters = {
        f["Properties"]["MetricTransformations"][0]["MetricName"]: f["Properties"]
        for f in resources("AWS::Logs::MetricFilter").values()
    }
    assert set(filters) == {"PullRequestsOpened", "IdentitiesMinted"}
    for f in filters.values():
        assert f["LogGroupName"] == {"!Ref": "FunctionLogGroup"}
    source = _service_info_lines()
    # Every route that opens a pull request logs "<kind> <id> opened <html_url> for <identity>",
    # and a pull request's html_url carries /pull/.
    opened = re.findall(r'log\.info\("%s %s opened %s for %s"', source)
    opened += re.findall(r'log\.info\("submission %s opened %s for %s"', source)
    assert len(opened) == 3, opened  # proposals, appends, submissions
    assert filters["PullRequestsOpened"]["FilterPattern"] == '"opened" "/pull/"'
    # No line names a minted identity; the access log names the route and its 201.
    assert '"%s %s identity=%s status=%d ms=%d"' in source
    assert 'RouteSpec("POST", "/tokens", "identity:post_tokens"' in source
    assert "status_code=201" in (SERVICE / "identity.py").read_text("utf-8")
    assert filters["IdentitiesMinted"]["FilterPattern"] == '"identity:post_tokens" "status=201"'


def test_a_budget_watches_the_bill_and_reports_to_the_topic() -> None:
    budget = one("AWS::Budgets::Budget")["Properties"]
    limit = budget["Budget"]["BudgetLimit"]
    assert limit["Amount"] == {"!Ref": "MonthlyBudgetUsd"}
    assert limit["Unit"] == "USD"
    assert int(template()["Parameters"]["MonthlyBudgetUsd"]["Default"]) > 0
    for note in budget["NotificationsWithSubscribers"]:
        assert note["Subscribers"] == [
            {"SubscriptionType": "SNS", "Address": {"!Ref": "AlarmTopic"}}
        ]


def test_a_live_alias_exists_for_the_function() -> None:
    alias = one("AWS::Lambda::Alias")["Properties"]
    assert alias["Name"] == "live"
    assert alias["FunctionName"] == {"!Ref": "Function"}
