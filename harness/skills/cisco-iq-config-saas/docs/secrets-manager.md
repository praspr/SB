# AWS Secrets Manager — Config SaaS

Use this reference for any read or write against the workload `agent-secrets`
and related Config SaaS secrets. The same patterns apply to the
`validation-and-compliance` and `cbp-lifecycle-etl` secret families when
their secret IDs are used instead.

## Safety rules

- Treat `agent-secrets` as **shared infrastructure**. Confirm with the user
  before any write (add / change / remove key, whitespace cleanup, rollback)
  in dev or nprd.
- Do **not** perform writes against prod from this skill.
- Do **not** print secret payloads into chat. Prefer key names or selected
  redacted fields unless the user explicitly asks for full values.
- If `GetSecretValue` fails with `AccessDeniedException` against master
  account `905418369215`, you used the wrong profile (a `cx-platform-*`
  master profile). Switch to the assumed `platform-*-admin` workload profile
  per the table below. Do not "fix" this by switching to an unrelated
  profile.
- If access fails with a credential / SSO error, run `duo-sso` once and retry.
  Do not switch to a different profile to "work around" the error.

## Critical: pick the right AWS profile

`cx-platform-dev-admin`, `cx-platform-nprd-admin`, `cx-platform-prod-admin`,
and `cx-platform-prod-readonly` are **source / master** account profiles and
do **not** have Secrets Manager permissions on the workload secrets. You
must use the **assumed** profiles below for `GetSecretValue` /
`PutSecretValue`.

| Env        | AWS profile           | Workload account | Default AWS region |
|------------|-----------------------|------------------|---------------------|
| dev        | `platform-dev-admin`  | `361769598815`   | `us-west-2`         |
| nprd usw2  | `platform-nprd-admin` | `713881804551`   | `us-west-2`         |
| nprd apse2 | `platform-nprd-admin` | `713881804551`   | `ap-southeast-2`    |
| nprd euc1  | `platform-nprd-admin` | `713881804551`   | `eu-central-1`      |
| prod usw2  | `platform-prod-admin` | `047719623103`   | `us-west-2`         |
| prod apse2 | `platform-prod-admin` | `047719623103`   | `ap-southeast-2`    |
| prod euc1  | `platform-prod-admin` | `047719623103`   | `eu-central-1`      |

`platform-prod-readonly` and `cx-platform-prod-admin` are both **denied**
`secretsmanager:GetSecretValue` on the workload secrets. Use
`platform-prod-admin` for prod secret reads (subject to the no-prod-write
rule above).

## Secret ID matrix

### ConfigBP AI (`agent-secrets`)

| Env        | Secret ID                                                |
|------------|----------------------------------------------------------|
| dev        | `cx/usw2/dev01/configbp-ai/secrets/agent-secrets`        |
| nprd usw2  | `cx/usw2/nprd01/configbp-ai/secrets/agent-secrets`       |
| nprd apse2 | `cx/apse2/nprd01/configbp-ai/secrets/agent-secrets`      |
| nprd euc1  | `cx/euc1/nprd01/configbp-ai/secrets/agent-secrets`       |
| prod usw2  | `cx/usw2/prod01/configbp-ai/secrets/agent-secrets`       |
| prod apse2 | `cx/apse2/prod01/configbp-ai/secrets/agent-secrets`      |
| prod euc1  | `cx/euc1/prod01/configbp-ai/secrets/agent-secrets`       |

Region tokens in secret names use the short form (`usw2`, `apse2`, `euc1`),
not the full AWS region code.

### Other Config SaaS secret families

| Service area                              | Secret ID pattern                                                                          |
|-------------------------------------------|--------------------------------------------------------------------------------------------|
| cbp-engine / validation-and-compliance    | `cx/<region-token>/<env>01/validation-and-compliance/secrets/assessments-configuration-secrets` |
| cxp-cbp-etl lifecycle                     | `cx/<region-token>/<env>01/lifecycle/secrets/cbp-lifecycle-etl-secrets`                    |

## Read a secret

```bash
aws secretsmanager get-secret-value \
  --secret-id "cx/usw2/dev01/configbp-ai/secrets/agent-secrets" \
  --profile platform-dev-admin --region us-west-2 \
  --query SecretString --output text | python3 -m json.tool
```

For nprd / prod swap profile, region, and secret ID per the tables above.

## Add or change a key (read–merge–put)

`agent-secrets` is a single JSON blob. Always read the current value, mutate
in memory, then `put-secret-value` the entire merged JSON back. Never run
`put-secret-value` with a hand-written partial payload — it replaces the
whole secret.

```bash
SECRET_ID="cx/usw2/dev01/configbp-ai/secrets/agent-secrets"
PROFILE="platform-dev-admin"
REGION="us-west-2"

NEW=$(aws secretsmanager get-secret-value \
        --secret-id "$SECRET_ID" --profile "$PROFILE" --region "$REGION" \
        --query SecretString --output text \
      | python3 -c 'import json,sys; d=json.load(sys.stdin); d["NEW_KEY"]="NEW_VALUE"; print(json.dumps(d))')

aws secretsmanager put-secret-value \
  --secret-id "$SECRET_ID" --profile "$PROFILE" --region "$REGION" \
  --secret-string "$NEW" \
  --query '{Name:Name,VersionId:VersionId}' --output json
```

## Remove a key

```bash
NEW=$(aws secretsmanager get-secret-value \
        --secret-id "$SECRET_ID" --profile "$PROFILE" --region "$REGION" \
        --query SecretString --output text \
      | python3 -c 'import json,sys; d=json.load(sys.stdin); d.pop("KEY_TO_REMOVE", None); print(json.dumps(d))')

aws secretsmanager put-secret-value \
  --secret-id "$SECRET_ID" --profile "$PROFILE" --region "$REGION" \
  --secret-string "$NEW"
```

## Strip leading/trailing whitespace from all string values

Several `TRINO_TABLE_*` values have historically had trailing spaces that
break exact name lookups. Use this to clean them in one pass:

```bash
NEW=$(aws secretsmanager get-secret-value \
        --secret-id "$SECRET_ID" --profile "$PROFILE" --region "$REGION" \
        --query SecretString --output text \
      | python3 -c '
import json,sys
d = json.load(sys.stdin)
for k,v in list(d.items()):
    if isinstance(v, str): d[k] = v.strip()
print(json.dumps(d))')

aws secretsmanager put-secret-value \
  --secret-id "$SECRET_ID" --profile "$PROFILE" --region "$REGION" \
  --secret-string "$NEW"
```

## Rollback to the previous version

Every `put-secret-value` keeps the previous version as `AWSPREVIOUS`. To
roll back, fetch that version explicitly and re-put it:

```bash
aws secretsmanager get-secret-value \
  --secret-id "$SECRET_ID" --profile "$PROFILE" --region "$REGION" \
  --version-stage AWSPREVIOUS --query SecretString --output text \
  | xargs -0 -I{} aws secretsmanager put-secret-value \
      --secret-id "$SECRET_ID" --profile "$PROFILE" --region "$REGION" \
      --secret-string {}
```

## Fetching `TRINO_SERVICE_CREDENTIALS` for ad hoc Trino/APISIX queries

For raw Trino queries through `local_apisix_setup.sh` (`docs/apisix-trino-internals.md`) —
not needed for `run_iceberg_query.sh`, which authenticates via a plain
`platform-<env>-admin` SSO profile instead.

When the shell running an ad hoc Trino query does not already have
`TRINO_SERVICE_CREDENTIALS` set, resolve it from this secret instead of
stopping and asking the user.

### Agent rule

If the user is in an interactive turn and the credential is missing:

- Pick the right **assumed** workload profile, AWS region, and `agent-secrets`
  secret ID for the env/region the query is actually targeting (use the
  tables under "Critical: pick the right AWS profile" and "ConfigBP AI
  (`agent-secrets`)" above). Do not reuse a credential fetched for a
  different env or region — APISIX maps each credential to a per-env
  consumer UUID, and a mismatched credential will fail with
  `cannot impersonate user`.
- Run the recipe below in a subshell.
- Export the resolved value into the shell that runs the query.
- Do **not** write the resolved value back to any `.env` file, paste it
  into chat, or include it in logs or commit messages. Treat it as a
  live credential.

### Recipe (parameterized)

Set `ENV`, `REGION`, then derive `PROFILE` and `SECRET_ID` from the
tables above. The `python3` step picks `TRINO_SERVICE_CREDENTIALS` out
of the JSON payload without printing the whole secret.

```bash
ENV="nprd"          # dev | nprd | prod
REGION="us-west-2"  # us-west-2 | ap-southeast-2 | eu-central-1
REGION_TOKEN="usw2" # usw2 | apse2 | euc1     (short form used in secret IDs)
ENV_LABEL="${ENV}01"

case "$ENV" in
  dev)  PROFILE="platform-dev-admin"  ;;
  nprd) PROFILE="platform-nprd-admin" ;;
  prod) PROFILE="platform-prod-admin" ;;
esac

SECRET_ID="cx/${REGION_TOKEN}/${ENV_LABEL}/configbp-ai/secrets/agent-secrets"

TRINO_SERVICE_CREDENTIALS=$(aws secretsmanager get-secret-value \
  --secret-id "$SECRET_ID" --profile "$PROFILE" --region "$REGION" \
  --query SecretString --output text \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["TRINO_SERVICE_CREDENTIALS"])')
export TRINO_SERVICE_CREDENTIALS

# Sanity check that DOES NOT reveal the value:
[[ -n "$TRINO_SERVICE_CREDENTIALS" ]] && echo "ok (len=${#TRINO_SERVICE_CREDENTIALS})"
```

### Failure modes

- `AccessDeniedException` against master account `905418369215`:
  you used a `cx-platform-*` master profile. Switch to the assumed
  `platform-*-admin` workload profile and retry.
- SSO / credential / expired-token error: run `duo-sso` once and retry.
  Do not switch profiles to "work around" the error.
- The python step prints `KeyError: 'TRINO_SERVICE_CREDENTIALS'`: the
  target secret exists but does not have that key. Confirm you targeted
  the right env/region — fall back to listing the keys with
  `... | python3 -c 'import json,sys; print(sorted(json.load(sys.stdin).keys()))'`
  before escalating.

### Common mistake

Do not confuse `TRINO_SERVICE_CREDENTIALS` with `SERVICE_CREDENTIALS`.
Only the former is authorized for Iceberg queries through APISIX. See
[`apisix-trino-internals.md`](apisix-trino-internals.md) for the
credential → principal mapping that makes this distinction matter.

## Fetching `BDB_CLIENT_ID` / `BDB_CLIENT_SECRET` for account lookup

Workflow context (when to use, commands, parsing the response):
[`platform-account-lookup.md`](platform-account-lookup.md).

`query_cisco_iq_account.sh` **auto-fetches** both keys on first run when they
are not already set in the shell or `$SKILL_DIR/.env`, then writes them to that
gitignored file for reuse.

Manual fetch (same source the script uses):

```bash
SECRET_ID="cx/usw2/dev01/configbp-ai/secrets/agent-secrets"
PROFILE="platform-dev-admin"
REGION="us-west-2"

aws secretsmanager get-secret-value \
  --secret-id "$SECRET_ID" --profile "$PROFILE" --region "$REGION" \
  --query SecretString --output text \
  | python3 -c '
import json, sys
d = json.load(sys.stdin)
for k in ("BDB_CLIENT_ID", "BDB_CLIENT_SECRET"):
    v = str(d.get(k, "")).strip()
    print(f"{k}: {'ok' if v else 'MISSING'} (len={len(v)})")
'
```

Do not paste the secret values into chat. If `GetSecretValue` fails, run
`duo-sso` once and retry with `platform-dev-admin` (not `cx-platform-*`).
