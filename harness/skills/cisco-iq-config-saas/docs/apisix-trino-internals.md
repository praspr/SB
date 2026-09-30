# APISIX → Trino internals

For ad hoc APISIX/Trino debugging via `local_apisix_setup.sh`. These notes
describe how to build a Trino client against the local APISIX tunnel,
based on the design of a prior bundled implementation.

## Prerequisite: team-standard kubeconfig aliases + APISIX tunnel

Iceberg/UDM queries through APISIX require two things in place:

1. The canonical kubeconfig context alias for the target
   (`cx-dev-usw2`, `cx-nprd-<region>`, `cx-prd-<region>`). Create or
   refresh it with the lightweight bundled helper — no sudo, no
   port-forward, no foreground hang:

   ```bash
   bash "$SKILL_DIR/scripts/setup_kube_context.sh" <env> [<region>]
   ```

2. A running APISIX port-forward against that target, started by
   `local_apisix_setup.sh <env> <region>`. That script also bootstraps
   the alias as a side effect, but it additionally takes sudo, edits
   `/etc/hosts`, and stays in the foreground — keep its terminal open
   while you run Iceberg queries.

   > **Agent note:** this port-forward is **user-run, not agent-run**.
   > Because it needs `sudo` and blocks in the foreground, an agent shell
   > call cannot start it. The agent must hand the user the exact
   > `local_apisix_setup.sh <env> [<region>]` command and wait for them to
   > confirm the tunnel is up. See
   > [`../SKILL.md`](../SKILL.md) → "APISIX agent behavior".

If your kubeconfig already uses a different context name for the same
EKS cluster, set `KUBE_CONTEXT=<your-context>` per call. See
[`../SKILL.md`](../SKILL.md) → "Kubernetes Context Naming (Team-Wide)"
for the full matrix and override semantics.

## Connection parameters (host / port / TLS verify)

A Trino client against this tunnel should lock the following, matching
the design of the prior bundled implementation: expose none of these
as user-tunable knobs.

| Setting    | Locked value                                          | Why it's locked                                                                                                                                  |
| ---------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| host       | `apisix-gateway.apisix.svc.cluster.local`             | This is the SNI / Host header APISIX expects. The setup script pins it to `127.0.0.1` in `/etc/hosts` so it resolves through the local tunnel.   |
| port       | `443`                                                 | The local port-forward listens on `443`. APISIX terminates TLS there.                                                                            |
| TLS verify | **always `False`** (no `--insecure`, no env override) | The local-tunnel endpoint always serves a **self-signed cert** for the internal hostname above; no public CA can validate it, so verification cannot succeed. Letting the user set `verify=true` would only cause every query to fail with a misleading "certificate verify failed" error. |

Treat env vars **`TRINO_HOST`**, **`TRINO_PORT`**, **`TRINO_SSL_VERIFY`**,
and **`TRINO_SSL_CA_PATH`** as fixed constants, not user-tunable
overrides — hardcode and `unset` them rather than reading from `.env` or
shell exports.

Still tunable per call: `TRINO_FORWARDED_PATH`, `TRINO_SERVICE_CREDENTIALS`,
`TRINO_SERVICE_USER`, `TRINO_QUERY_TIMEOUT`, catalog/schema.

> Security note for reviewers: hardcoding `verify=False` is a deliberate,
> scoped exception to the standard "always verify TLS" guideline. It is
> safe here because the only reachable endpoint is `127.0.0.1` over a
> kubectl port-forward that the operator just established — the
> connection never leaves the host. Re-evaluate if ever pointed at a real
> Trino endpoint.

## Credential format and the principal-UUID indirection

The Iceberg credential format is `base64(client_id:client_secret)`. The
`client_id` you see when you base64-decode `TRINO_SERVICE_CREDENTIALS` is
**not** the Trino principal.

APISIX maps each credential's `client_id` to an **internal consumer UUID**
and forwards that consumer UUID as `X-Trino-User`. Trino then enforces
that `X-Trino-User` equals the consumer principal — which is **not** the
same value as the `client_id`.

APISIX consumers are scoped per **env** (`dev` / `nprd` / `prod`), not per
region. The same `TRINO_SERVICE_CREDENTIALS` value is accepted by every
region in an env, and APISIX maps it to the same internal consumer UUID
across those regions — a principal cache keyed on env alone (not
env+region) is valid.

Worked example shape (UUID values shown as placeholders; never paste the
real values into docs, commits, or chat):

| Credential                    | `client_id` (left half of decoded cred)        | Trino principal APISIX forwards                                          |
|-------------------------------|------------------------------------------------|--------------------------------------------------------------------------|
| `TRINO_SERVICE_CREDENTIALS`   | `<client_id_a>` (UUID, for Iceberg consumer)   | **`<consumer_uuid_a>`** (different UUID, harvested from Trino at runtime)|
| `SERVICE_CREDENTIALS`         | `<client_id_b>` (UUID, for the Aurora API consumer) | same APISIX consumer namespace, **not** authorized for Iceberg          |

This is the reason Iceberg queries **must** use `TRINO_SERVICE_CREDENTIALS`
and not `SERVICE_CREDENTIALS`, even though both decode to plausible
UUID-shaped client IDs.

## Discovering the principal without hardcoding it

1. Send a probe `SELECT 1` with a placeholder `X-Trino-User`.
2. Parse the resulting Trino error:

   ```text
   User <X> cannot impersonate user <Y>
   ```

3. Cache the harvested `<X>` per env (mode `0600`) and reuse it for
   subsequent calls in any region of that env — no need to re-probe.

Support an override for the discovered value (CLI flag and/or env var).

If discovery fails entirely, fall through to a placeholder — Trino
surfaces a clear `cannot impersonate user <X>` error. Copy `<X>` from the
error into the override to get unblocked.

Flush the cache when:

- APISIX consumer UUID changes (credential rotation that includes
  re-issuing the consumer).
- The `TRINO_SERVICE_CREDENTIALS` value changes in
  `agent-secrets`.
- A previously working target starts returning `cannot impersonate user`
  with a UUID different from the cached one.

Cache files contain credential-derived data — never commit them or paste
their contents into chat, commits, logs, or skill files.

## macOS DNS quirk (`.local`)

The K8s-internal hostname `apisix-gateway.apisix.svc.cluster.local` ends in
`.local`, which macOS routes through Bonjour/mDNS — bypassing `/etc/hosts`.
Pin this hostname to `127.0.0.1` directly:

- curl: `--resolve apisix-gateway.apisix.svc.cluster.local:443:127.0.0.1`
- python: a `socket.getaddrinfo` monkey-patch that overrides resolution.

Disable the pin with `TRINO_DNS_PIN=0` if you ever point at a real
DNS-resolvable Trino host. On Linux the pin is unnecessary but harmless.

## Iceberg schema-name pattern

The Glue catalog name is per env + region. SQL must double-quote the
hyphenated schema name:

```text
iceberg."cx-<region-token>-<env>01-datafabric-glue-catalog"
```

Examples:

| Target     | Schema                                                  |
|------------|---------------------------------------------------------|
| dev usw2   | `iceberg."cx-usw2-dev01-datafabric-glue-catalog"`       |
| nprd usw2  | `iceberg."cx-usw2-nprd01-datafabric-glue-catalog"`      |
| nprd apse2 | `iceberg."cx-apse2-nprd01-datafabric-glue-catalog"`     |
| nprd euc1  | `iceberg."cx-euc1-nprd01-datafabric-glue-catalog"`      |
| prod usw2  | `iceberg."cx-usw2-prod01-datafabric-glue-catalog"`      |
| prod apse2 | `iceberg."cx-apse2-prod01-datafabric-glue-catalog"`     |
| prod euc1  | `iceberg."cx-euc1-prod01-datafabric-glue-catalog"`      |

UDM table version suffixes (e.g. `udm_device_command_1__0__7`) are bumped
independently by the data fabric team — confirm live versions with
`SHOW TABLES FROM iceberg."cx-<region-token>-<env>01-datafabric-glue-catalog"`
before writing version-pinned SQL (or, for the Athena path, `SHOW TABLES` via
`run_iceberg_query.sh`, no schema qualifier needed there). See
[`table-registry.md`](table-registry.md) for the current canonical names.

## Joining Iceberg ↔ Aurora

`udm_device_command_*` carries only `asset_key` (no serial, no hostname,
no `platform_account_id`). To bridge to a finding or an asset:

1. Pull `asset_key` from Aurora via `run_postgres_query.sh` (typically from
   `assessmentsapp__table__unified_config_assmt_finding_pg` or `assets__table__cvi_assets_view`).
2. Use that `asset_key` in the Iceberg `udm_device_command_*` `WHERE` clause.
