# LangSmith Trace Analysis (configbp-ai agent traces)

Analyze LangSmith traces to diagnose configbp-ai (`ciq-agents-*`) agent runs
— routing decisions, tool calls, LLM calls, token usage, errors — or any
public LangSmith trace from another instance. Ported from the standalone
`langsmith-trace` skill in `configbp-ai`; kept in sync manually if that skill
changes.

Two flows:

- **Public shared URL** (`/public/<token>/r`) — no auth →
  `scripts/fetch_langsmith_trace.py`
- **ConfigBP-AI authenticated search** (browser URL, Jira feedback ticket, or
  a thread/account/user id) → `scripts/search_langsmith_runs.py`

## When to use

- User shares a LangSmith trace URL (`/public/<share_token>/r` **or** a
  browser URL like
  `https://langsmith.<env>.../o/<org>/projects/p/<proj>?peek=<run_id>`)
- User pastes a Jira AI-feedback ticket (`IQ-in-app-feedback`, e.g. `CXP-39009`)
- User gives a `thread_id`, `platform_account_id`, or `user_id` to investigate
- User asks to debug, review, or understand a configbp-ai agent run
- User wants token usage, cost, latency, tool-call, or error-pattern analysis

## Prerequisites

`search_langsmith_runs.py` auto-provisions its own credentials — same
resolution order and auto-fetch pattern as
[`scripts/query_cisco_iq_account.sh`](../scripts/query_cisco_iq_account.sh)'s
`BDB_CLIENT_ID`/`BDB_CLIENT_SECRET`:

1. Existing shell env
2. This skill's `.env` (gitignored)
3. Auto-fetch: pulls `cx/usw2/<nprd|prod>01/configbp-ai/secrets/agent-secrets`
   via `aws secretsmanager get-secret-value` (profiles
   `platform-nprd-admin`/`platform-prod-admin`, region `us-west-2`) — only
   two LangSmith **instances** exist (dev traces land on the nprd instance
   and reuse its creds, so there's no separate dev secret to fetch).
   Each secret carries *generic* key names (`LANGSMITH_API_KEY`,
   `LANGSMITH_ENDPOINT`, `LANGSMITH_PROJECT`, ...) scoped to that AWS
   account — the script remaps them to `LANGSMITH_NPRD_*`/`LANGSMITH_PROD_*`
   before writing, so both instances' keys can coexist in one `.env` without
   clobbering each other. Written into this skill's `.env` (created if
   missing, `chmod 600`) so later runs skip straight to step 2. On an auth
   failure it retries once via `duo-sso`, same as the BDB-credential fetch.

No manual setup needed — just run the script; it fetches what it's missing.
If `aws`/`duo-sso` access is broken, it prints which secret/profile failed.

`search_langsmith_runs.py` requires the `langsmith` Python SDK
(`uv pip install langsmith`); `fetch_langsmith_trace.py` (public traces only)
uses only the stdlib and does not need these credentials, though it will pick
up `LANGSMITH_API_KEY`/`LANGSMITH_ENDPOINT` from the shell env if present —
run `search_langsmith_runs.py` once first (or `source .env`) to populate them.

## ConfigBP-AI static reference (do not re-discover)

Two LangSmith instances. `dev` and `nprd` traces both land on the **nprd**
instance; `prod` is separate.

| Env tier | Endpoint | Org/tenant ID |
|---|---|---|
| dev + nprd | `https://langsmith.nprd.usw2.plat.cxp.csco.cloud/api/v1` | `39da314d-30b7-4d39-885f-a09c95afc738` |
| prod | `https://langsmith.prod.usw2.plat.cxp.csco.cloud/api/v1` | `b90144f2-f89a-4234-99c0-c04f451fbd91` |

Browser URL shape (for parsing a pasted UI link):
`https://langsmith.<env>.<region>.plat.cxp.csco.cloud/o/<org>/projects/p/<project_id>?...&peek=<run_id>&peeked_trace=<trace_id>`

Project name pattern: `ciq-agents-<env>-<region>`. `search_langsmith_runs.py`
has the project-id map for `usw2`/`apse2`/`euc1` × dev/nprd/prod baked in —
pass `--env`/`--region`, not the raw project id.

Region tokens (Jira `Region` field → `<region>` token):
`us-west-2`→`usw2`, `ap-southeast-2`→`apse2`, `eu-central-1`→`euc1`.

## Trace shape (stable facts)

- Root run is `Semantic Router` (interactive Q&A) or `FeedbackGraph`
  (thumbs-up/down event). The `Configuration Agent` seen in the UI filter is
  a **child** run, not the root.
- `thread_id` lives in root-run `extra.metadata.thread_id`, equal to
  `inputs.payload.context.context_id` — the join key from a Jira feedback
  ticket's `threads/<id>` URL segment to its trace.
- `platform_account_id`/`user_id`/`user_name` live on **child** runs
  (`ls_run_depth` 3–5), not the root — search with `is_root=False`, dedupe by
  `trace_id`, then fetch each root.
- Root `outputs.output` is the final answer; `outputs.agent_choice` is the
  routed agent (`null` = `out_of_scope`, a `success` status not an error).

## Procedure

### Jira feedback ticket flow

1. Fetch the ticket (atlassian MCP `jira_get_issue`). Parse `thread_id` (the
   `threads/<uuid>` segment of the `Page / URL` field), `env` (`Environment`
   field), and `region` (via the region-token table above).
2. `python3 scripts/search_langsmith_runs.py --thread-id <thread_id> --env <env> --region <region>`
3. A feedback thread typically returns multiple roots: `Semantic Router`
   (the Q&A) and `FeedbackGraph` (the thumbs event) — analyze the
   `Semantic Router` root.
4. If `--region` from Jira returns no matches, retry `usw2` — prod traces
   are often in `ciq-agents-prod-usw2` even when Jira says a different region.

### `search_langsmith_runs.py` modes

`--mode list` (one summary per match) · `overview` (default for a single
trace: routing path, tools, llm-call count, errors, tokens) · `feedback`
(root-cause bundle, see below) · `tree` (full nested run tree, every child
run) · `tools` (tool call args/results) · `llm` (each LLM call's
inputs/outputs) · `raw`.

```bash
python3 scripts/search_langsmith_runs.py --thread-id <id> --env prod --mode overview
python3 scripts/search_langsmith_runs.py --thread-id <id> --env prod --mode feedback
python3 scripts/search_langsmith_runs.py --thread-id <id> --env prod --mode tree
python3 scripts/search_langsmith_runs.py --platform-account-id <id> --env prod --mode list
python3 scripts/search_langsmith_runs.py --run-id <id> --env nprd --mode tools
```

### Routing gate — do this first on any Semantic Router trace

Before analyzing tool calls, LLM answers, tokens, or downstream agent
behavior, determine whether the Semantic Router sent the request to the
**right** agent:

1. `--mode feedback` or `overview` for `summary.agent_choice`, `ui_context`,
   `summary.question`, `routing_path`.
2. `--mode llm` on the same `run_id` for the router's own system prompt and
   candidate-agent list (lives on depth-2 nodes like `route_to_agent`,
   `fetch_agent_candidates_db` — not in the answering agent's system prompt).

Compare: user question, UI context (`app`/`url`/`source`/`filters`), routed
agent (`agent_choice`), and the router prompt's declared rules. State
**Correct routing** or **Mis-routed** explicitly, citing the evidence.
Mis-routed when: page context implies one domain but `agent_choice` points
elsewhere; the question fits agent A per the router prompt but agent B was
picked; `routing_method` is `semantic` but the chosen agent's description
doesn't cover the question/entity type; or `out_of_scope` was returned while
a listed candidate clearly matches.

If mis-routed, say so prominently before anything else — downstream tool
failures may be a symptom, not the root cause.

### Negative-feedback root cause ("why did the user dislike this answer?")

1. Get the ticket, parse `thread_id`/`env`/`region` (Jira flow above). Note
   the stated `Reason(s)`/`Comment`.
2. `python3 scripts/search_langsmith_runs.py --thread-id <id> --env <env> --region <region> --mode feedback`
   — returns per Q&A turn: `summary.question`/`.answer`/`.agent_choice`,
   `routing_path`, and `answering_agents[]` (each non-guardrail LLM call's
   `system_prompt`, `ui_context`/`ui_context_present`, `conversation_history`,
   `user_message`, `answer`).
3. Run the routing gate above.
4. Classify: **mis-routed** / **genuine missing functionality** (routing
   correct, request outside the agent's declared scope, correctly declined —
   a product gap) / **in-scope but mis-handled** (routing correct, request
   fits scope, but declined/wrong-entity/tool-or-LLM error — a fixable
   defect) / **context mismatch** (routing correct, but UI context or
   conversation history steered the agent wrong).

Present sections in this order: **routing verdict** → Q&A summary → downstream
analysis (tools/errors/tokens/answer quality).

### Public trace procedure (non-configbp, or a public share link)

```bash
python3 scripts/fetch_langsmith_trace.py "<TRACE_URL>" --mode overview
```

Modes: `overview` (default — metadata, run tree, tokens) · `full` ·
`messages` · `tokens` · `tools` · `raw`. Present model/provider/duration,
run tree, input/output, error summary, and token summary (per-step +
cumulative, cache hit rate).

## Analysis checklist

**Errors**: repeated identical tool calls (blind retries), transient (5xx)
vs. client (4xx/validation) errors, misleading error messages, missing
error handling.

**Token efficiency**: prompt cache hit rate, reasoning-token proportion,
token growth across retries, context-window usage.

**Agent behavior**: does it adapt after failures, are tool args well-formed,
does it follow its system prompt, is `finish_reason` appropriate.

**Latency**: total + per-step duration, bottleneck step.

## Output format

Markdown with clear headers; **routing verdict first** on ConfigBP-AI
traces; tables for token/step data; JSON code blocks for tool args and raw
data; truncate long system prompts/tool responses for readability. All data
must come from the trace — never invent or assume trace content.
