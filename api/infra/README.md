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

## Running it on this machine

The founder's git-ignored `.env` carries the same GitHub App values (the local door of C8), so
the whole service runs from a laptop against the real graph:

```sh
set -a; . ./.env; set +a
PYTHONPATH=api:gate uv run python -m opn_api.local --port 8000
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
  read (F07 opens pull requests with these; F05 uses only the OAuth identity).
- **Install** on the graph repository only.

## Repository variables the deploy workflow reads

Set from the stack outputs (`gh variable set NAME --body VALUE`):
`OPN_API_DEPLOY_ROLE_ARN`, `OPN_API_FUNCTION_NAME`, `OPN_API_URL`, `OPN_AWS_REGION`.

On the **graph** repository, set `OPN_API_CLAIMS_URL` to the stack's `ClaimsUrl` output — but
only once its `gate-spec.json` pins a `network` commit whose gate understands `--claims-url`
(F05-R10). Until then the post-merge job simply omits the flag and the committed `claims.json`
stands.
