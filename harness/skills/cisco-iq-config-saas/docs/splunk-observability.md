# Splunk Observability (SignalFx APM) Access

How to pull APM trace data (span timing, service breakdown) for a Cisco IQ
Config SaaS trace ID, without a browser.

## Prerequisites

- `SPLUNK_API_TOKEN` should be available as a global shell env var (exported
  in `~/.zshrc`) — source it first (`source ~/.zshrc`) since a fresh Bash
  invocation won't pick it up automatically. It's also set in this repo's
  `.env` as a fallback. `run_splunk_trace_query.sh` checks both, and if
  neither has it, prompts interactively and saves the entered token to
  `~/.zshrc`/`~/.bashrc` for next time — do not search the repo/secrets
  stores for a substitute token.
  - **If the user manually exports `SPLUNK_API_TOKEN`** in the shell (e.g.
    via `! export SPLUNK_API_TOKEN='...'`) instead of letting the script
    prompt for it, the script's own persist logic never runs (it only fires
    on its own interactive prompt) — the token would otherwise vanish at
    session end. The agent should persist it itself right after seeing it
    exported, so it survives across sessions — write it to the user's
    global shell rc file (`~/.zshrc`/`~/.bashrc`, matching `$SHELL`), same
    as the script's own prompt path does. Not the repo's `.env` — that's
    the fallback location, not where manually-supplied tokens should land.
  - **To get a token**: `https://cisco-cx-observe.signalfx.com` -> top-right
    profile menu -> **My Profile** -> **"Show User API Access Token"**
    button (top right of that page) -> copy it.
- Org: Cisco Systems Inc., UI at `https://cisco-cx-observe.signalfx.com`.
- **Realm: `us1`** (confirmed via the organization endpoint below — the
  custom UI domain does not map directly to the API host, don't guess other
  realms first).

## Getting the trace ID

Every `cxp-baqs` GraphQL request carries a `traceparent` request header:

```
traceparent: 00-<32-hex-trace-id>-<16-hex-span-id>-01
```

Pull it from a captured HAR file, a `get_network_request` call, or the
`server-timing` response header (same trace ID, different span). Or grab it
straight from the browser: DevTools -> **Network** tab -> reproduce the
slow action -> click the `cxp-baqs` request (e.g. `graphql` or `api/*`) ->
**Headers** -> **Request Headers** -> `traceparent`.

**The user may paste either the bare 32-hex trace ID or the full
`traceparent` header value** (e.g.
`00-8d9eff3093e1ef18834cff06060ef710-df79bac305cbb7eb-01`) — the agent
should extract the trace ID itself rather than asking the user to do it:
it's the second `-`-delimited field (32 hex chars), between the `00`
version byte and the 16-hex span ID. In the example above, the trace ID is
`8d9eff3093e1ef18834cff06060ef710`. The
32-hex segment is the trace ID used below and in the UI URL
`https://cisco-cx-observe.signalfx.com/#/apm/traces/<trace-id>`.

## Validate the token / confirm realm

```bash
SPLUNK_API_TOKEN=$(grep "^SPLUNK_API_TOKEN=" .env | cut -d'=' -f2- | tr -d '"'"'"'')
curl -s -H "X-SF-Token: $SPLUNK_API_TOKEN" \
  "https://api.us1.signalfx.com/v2/organization"
```

200 with `"organizationName": "Cisco Systems Inc."` confirms both the token
and the `us1` realm are correct.

**Gotcha**: don't `source .env` directly in the shell — this repo's `.env`
resets `PATH` as a side effect, which breaks `curl`. Extract just the one
key with `grep`/`cut` as shown above instead.

## Fetching a trace

The public REST trace-download API (`/v2/trace/{traceId}` etc.) returns
404 for this org — traces here are served through the same **GraphQL**
endpoint APM2's UI uses:

```
POST https://api.us1.signalfx.com/v2/apm/graphql
```

`scripts/run_splunk_trace_query.sh` wraps token resolution + the GraphQL
POST + waterfall/SQL formatting:

```bash
bash "$SKILL_DIR/scripts/run_splunk_trace_query.sh" <trace-id>            # waterfall
bash "$SKILL_DIR/scripts/run_splunk_trace_query.sh" <trace-id> --sql      # just db.statement spans
bash "$SKILL_DIR/scripts/run_splunk_trace_query.sh" <trace-id> --json     # raw response, e.g. to save as trace.json
```

**The script only covers the three modes above (waterfall, `--sql`, raw
`--json`) — it's not a full GraphQL client.** If exploring a trace needs
something the script doesn't expose (extra fields like `parentSpanID`,
filtering by `serviceName`, a different query shape, pagination workarounds
for the truncation gotcha below, etc.), the agent is free to hit
`https://api.us1.signalfx.com/v2/apm/graphql` directly with `curl` using the
same `X-SF-Token` header, rather than being limited to the script's flags.

Introspection is disabled (`INTROSPECTION_DISABLED`), so the schema has to
be discovered by trial — GraphQL validation errors are informative and
include "Did you mean ...” suggestions (e.g. `duration` not
`durationMicros`, `startTime` not `startTimeUnixNano`). Notes on the shape
the script relies on:

- `trace(id: ID!)` — argument is `id`, not `traceId`.
- `duration` and `startTime` are in **microseconds** (not nanoseconds).
- Spans come back unordered — sort by `startTime` client-side to read the
  waterfall.
- Fields confirmed to exist: `spanID`, `operationName`, `serviceName`,
  `duration`, `startTime`, `tags`. Other likely fields (`parentSpanID`,
  `kind`) were not yet confirmed working — probe with a minimal query first
  and read the validation error for the real field name before assuming a
  shape.

## Finding the exact DB query behind a slow span

`tags` is a `[KeyValueTypeField!]` — the `--sql` flag requests
`{ key value }` subfields and filters to spans carrying a `db.statement`:

```bash
bash "$SKILL_DIR/scripts/run_splunk_trace_query.sh" <trace-id> --sql
```

For any span instrumented with OpenTelemetry DB semantics (`pg.query:...`,
JDBC `SELECT ...`, etc.), the `tags` array carries the **full literal SQL**
under the key `db.statement` (also duplicated as `db.query.text`) — bind
parameters already substituted where the driver logs them inline (e.g. the
`@opentelemetry/instrumentation-pg` Postgres spans include fully-resolved
`WHERE` clauses; JDBC/Hibernate spans often still show `?` placeholders).

This is the fastest way to confirm *exactly* what Postgres/Trino executed —
no need to reconstruct the query from resolver templates (`baqs.json`)
and guess at OPA-injected row filters. Cross-check the reconstructed
version against this if you built one by hand first; OPA-injected
`WHERE` clauses (row-level security predicates) will show up here even
though they aren't in the resolver's static SQL template.

## Reading the result

Sort spans by `startTime`, compute each span's offset from the trace's
first span, and scan for the operation whose `duration` accounts for most
of the total trace time — that's the actual bottleneck, as opposed to
guessing from client-side request duration alone.

## Two different traffic paths — different service names, different SQL shape

This org's traces cover (at least) two unrelated stacks. Check `serviceName`
first to know which one you're looking at before interpreting `db.statement`.

### cxp-query-service (UI/API path, `cxp-baqs` GraphQL)

Service names: `apisix-gateway`, `cxp-iam-auth-server` (Java/Spring, JDBC —
`?` placeholders), `cxp-query-service` (Node, `pg` driver — **values already
inlined**), `openfga`. `db.statement`/`db.query.text` on `cxp-query-service`
spans (`pg.query:SELECT ...`) is directly usable — no further lookup needed.

### configbp-ai (agent chat path)

Service names: `cvi-ai-a2a-semantic-router` (upstream router) →
`configbp-ai-a2a-server` → `configbp-ai-agent` → `configbp-ai-mcp-server` →
`trino` (+ `cxp-iam-auth-server`, `openfga`, `ai-platform-serving` as
dependencies). Getting the trace ID here: extract `traceparent` from the
`agent`/`mcp_server` request headers, or read `otel_trace_id` directly out of
mcp_server's own JSON logs / audit event (`tool_call.completed`) — every log
line emitted during a tool call carries it. It also shows up (extraction
only, not live span-linked) in LangSmith run metadata as `otel_trace_id`.

**Gotcha — the GraphQL `trace()` query silently truncates on large traces.**
No pagination arg exists (confirmed: `first` is rejected as unknown), and
observed span counts returned (~746) were far short of what the Splunk UI's
own trace view shows for the same trace ID (4542 spans loaded). Deeply
nested spans — in particular the actual `SELECT ... FROM
assessmentsapp__table__unified_config_assmt_finding_pg WHERE ...` spans
under `trino: Metadata.getRedirectionAwareTableHandle` — were present in the
UI but absent from every GraphQL fetch tried. **For large configbp-ai
traces, use the Splunk UI directly** (search/filter by table name in the
waterfall, e.g. `assessmentsapp_ta...`) rather than trusting the GraphQL
API's span list to be complete. Use the GraphQL API for the
top-level flow/timing breakdown and small traces; fall back to the UI
screenshot for buried connector-level SQL spans.

**Trino's postgresql-connector spans are JDBC-style — `?` placeholders,
no bound values.** Unlike `cxp-query-service`'s inlined-value spans, Trino's
`db.statement` here is the parameterized SQL as sent to the JDBC prepared
statement (e.g. `WHERE "execution_id" IN (?) AND "platform_account_id" = ?`).
The bound values aren't in the trace or in mcp_server's audit log (which only
stores a `query_hash`, not raw values, by design). To recover them:
- `platform_account_id` is usually already in the audit log line itself.
- `execution_id` typically isn't logged anywhere — reconstruct it by querying
  Aurora directly for the most recent `engine_status = 'COMPLETED'` row for
  that `platform_account_id` as of the request timestamp (via this skill's
  `run_postgres_query.sh`), since `query_findings`-style tools resolve
  "latest completed execution" internally rather than taking it as an
  explicit param. Treat this as an inference, not a value read verbatim from
  a log/span — say so when reporting it.
