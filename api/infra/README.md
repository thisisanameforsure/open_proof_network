# api infrastructure (F05-R12)

The service answers on `https://api.openproofnetwork.org`, and on its generated
`…execute-api.us-east-1.amazonaws.com` address as well.

`api.cfn.yaml` is the whole stack: the function, the HTTP API, three DynamoDB tables, the
execution role, and the deploy role CI assumes through OIDC. It is created once from the
founder's `.env` credentials (C8 item 5); after that nothing but the function's *code* changes,
and only `api-deploy.yml` changes it.

## Bootstrap

```sh
set -a; . ./.env; set +a
export AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY"          # the .env names it AWS_ACCESS_KEY
aws cloudformation deploy \
  --stack-name opn-api --region us-east-1 \
  --template-file api/infra/api.cfn.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    ApiDomain=api.openproofnetwork.org \
    CertificateArn="$CERT_ARN" \
    HostedZoneId="$ZONE_ID"
aws cloudformation describe-stacks --stack-name opn-api --region us-east-1 \
  --query 'Stacks[0].Outputs' --output table
```

The site stack already created the GitHub OIDC provider, so `CreateOidcProvider` defaults to
`false` here. The trust policy is pinned to the numeric GitHub owner and repository ids: the
`sub` claim is `repo:owner@<id>/name@<id>:ref:refs/heads/main`, and the ids survive renames.

## Limits, alarms and protection (F05-T22)

The stack carries the service's guards against a flood and a runaway bill: stage throttling on
every route (`ThrottleBurstLimit`, `ThrottleRateLimit`), a reserved-concurrency ceiling on the
function (`ReservedConcurrency`), `Retain` deletion and replacement policies plus point-in-time
recovery on all three tables, one SNS topic (`AlarmTopic`, optionally mailed to `AlarmEmail`),
CloudWatch alarms on the API's 4xx and 5xx and the function's throttles, errors and invocations,
two log metric filters (`OPN/api` `PullRequestsOpened`, `IdentitiesMinted`) with an alarm each,
and a monthly cost budget for the **whole account** (`MonthlyBudgetUsd`) reporting to the topic.

The function's logs move to Lambda's JSON format at INFO. Under the plain-text default Lambda
keeps WARN and above only, and the runtime's own root handler makes `logging.basicConfig` a no-op,
so the access line and the "opened" line the filters match would never reach CloudWatch. The
message text inside each JSON event is unchanged.

### Applying it: a change set, read before it is executed

`aws cloudformation deploy` cannot keep a parameter's previous value, so every parameter the live
stack already has is passed with `UsePreviousValue=true`, and only the new ones are named.

```sh
set -a; . ./.env; set +a
export AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY"
export AWS_REGION=us-east-1

# 1. The reserved concurrency must leave 100 unreserved in the account; check the limit first.
aws lambda get-account-settings --query 'AccountLimit.[ConcurrentExecutions,UnreservedConcurrentExecutions]'

# 2. Every existing parameter keeps its value; the new ones are named here (defaults otherwise).
PREVIOUS=$(aws cloudformation describe-stacks --stack-name opn-api \
  --query 'Stacks[0].Parameters[].ParameterKey' --output text \
  | tr '\t' '\n' | sed 's/.*/ParameterKey=&,UsePreviousValue=true/' | tr '\n' ' ')
aws cloudformation create-change-set \
  --stack-name opn-api --change-set-name f05-t22-hardening \
  --template-body file://api/infra/api.cfn.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameters $PREVIOUS \
    ParameterKey=AlarmEmail,ParameterValue="$OPN_ALARM_EMAIL" \
    ParameterKey=MonthlyBudgetUsd,ParameterValue=50
aws cloudformation wait change-set-create-complete \
  --stack-name opn-api --change-set-name f05-t22-hardening

# 3. Read it. Every table must say Modify with Replacement False; nothing may say Remove.
aws cloudformation describe-change-set \
  --stack-name opn-api --change-set-name f05-t22-hardening \
  --query 'Changes[].ResourceChange.[Action,LogicalResourceId,ResourceType,Replacement]' \
  --output table

# 4. Only then execute, and wait.
aws cloudformation execute-change-set \
  --stack-name opn-api --change-set-name f05-t22-hardening
aws cloudformation wait stack-update-complete --stack-name opn-api
```

What the read should show: `Add` for the alias, the topic, its policy, the subscription (only
with an email), seven alarms, two metric filters and the budget; `Modify` with `Replacement
False` for the three tables, the function and the stage. Anything else, delete the change set
(`aws cloudformation delete-change-set ...`) and ask. The email subscription stays pending until
the address clicks the confirmation SNS sends it; alarms fire into the topic either way.

Then, as evidence: `curl -s https://api.openproofnetwork.org/health`, open a token through the
tutorial path once and check that `IdentitiesMinted` shows a 1
(`aws cloudwatch get-metric-statistics --namespace OPN/api --metric-name IdentitiesMinted ...`),
which is the first proof the filters see the log lines.

### The live alias

`LiveAlias` (`live`) exists and points at `$LATEST`; the HTTP API still invokes the unqualified
function. Moving the integration onto the alias is deliberately not done here: a published
version freezes the function's environment, so once the API answered from a version, a change set
that sets `UsesFrom` or `AnnexStepsFrom` would not reach the running service until the next code
deploy published a new version, and the deploy role would also need `lambda:UpdateAlias` on the
alias and a second invoke permission for the qualified ARN. It is its own task, with the order:
(1) stack: deploy-role `UpdateAlias`, an invoke permission on the alias; (2) workflow: publish,
then `update-alias --name live --function-version <published>`; one green deploy moving it;
(3) stack: integration onto the alias ARN, and every later environment change followed by a
deploy.

## Running it on this machine

The founder's git-ignored `.env` carries the same GitHub App values (the local door of C8), so
the whole service runs from a laptop against the real graph:

```sh
set -a; . ./.env; set +a
PYTHONPATH=api:gate:site uv run python -m opn_api.local --port 8000
curl -s localhost:8000/health          # {"ok": true, "store": "memory"}
```

It uses the in-process store, so identities and claims live only for that run, and its token
salt is a different value from the deployed one — a token minted locally does not work against
`api.openproofnetwork.org`, and the deployed salt never leaves Parameter Store. Because the App
values exist in both places, **a rotation has to change both**.

## The five secrets (C8 item 3)

The function reads these from Parameter Store at startup and from nowhere else. Put them there
once, as `SecureString`, under `/opn/api/`:

| Parameter | Where it comes from |
|---|---|
| `github-app-id` | the GitHub App's settings page, "App ID" |
| `github-client-id` | the same page, "Client ID" |
| `github-client-secret` | the same page, "Generate a new client secret" (shown once) |
| `github-private-key` | the same page, "Generate a private key" (a `.pem` download) |
| `token-secret` | generate locally: `openssl rand -base64 32` |

```sh
aws ssm put-parameter --name /opn/api/token-secret --type SecureString \
  --value "$(openssl rand -base64 32)" --region us-east-1
aws ssm put-parameter --name /opn/api/github-private-key --type SecureString \
  --value "file://$HOME/Downloads/opn-network.private-key.pem" --region us-east-1
```

Health returns 503 naming every parameter that is still missing (R13), so the service never
half-runs.

## The GitHub App

Create it under the founder's account (Settings → Developer settings → GitHub Apps → New):

- **Homepage**: `https://openproofnetwork.org/`. **Callback URL**:
  `https://api.openproofnetwork.org/auth/github/callback`. A GitHub App accepts several callback
  URLs, so the generated `…execute-api…` address may be listed alongside it while DNS settles.
  Tick **Request user authorization (OAuth) during installation**.
- **Webhook**: not needed at F05 — untick Active.
- **Permissions**: Repository → Contents read and write, Pull requests read and write, Metadata
  read (F07 opens pull requests with these; F05 uses only the OAuth identity), **Actions read and
  write** (F06 dispatches the precheck workflow on the scratch repository).
- **Install** on the graph repository and the precheck scratch repository, and on nothing else.

> **Actions: read and write is not granted yet.** The installation currently carries
> `{contents: write, metadata: read, pull_requests: write}`, so `POST /precheck` pushes its job
> branch and then fails the dispatch with `403 Resource not accessible by integration`. Adding a
> permission is the App owner's act — change it on the App, then approve the request on the
> installation — and F06-AC15 cannot close until it is done.
> `engineering/evidence/F06/task-5.txt` has the probe that tells granted from not granted without
> starting a workflow run.

## Repository variables the deploy workflow reads

Set from the stack outputs (`gh variable set NAME --body VALUE`):
`OPN_API_DEPLOY_ROLE_ARN`, `OPN_API_FUNCTION_NAME`, `OPN_API_URL`, `OPN_AWS_REGION`.

On the **graph** repository, set `OPN_API_CLAIMS_URL` to the stack's `ClaimsUrl` output — but
only once its `gate-spec.json` pins a `network` commit whose gate understands `--claims-url`
(F05-R10). Until then the post-merge job simply omits the flag and the committed `claims.json`
stands.
