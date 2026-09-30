#!/usr/bin/env python3
"""Search and analyze configbp-ai (ciq-agents-*) LangSmith traces by metadata.

Authenticated companion to fetch_trace.py. Where fetch_trace.py reads a single
public shared trace, this script searches an authenticated project for runs by
thread_id / account / user / run id and analyzes the configbp LangGraph trace
(root = Semantic Router / FeedbackGraph; routing, tool calls, LLM calls below).

Usage:
    python3 search_runs.py --thread-id <uuid>            [--env prod] [--region usw2]
    python3 search_runs.py --platform-account-id <uuid>  [--env nprd]
    python3 search_runs.py --user-id <uuid>              [--env prod]
    python3 search_runs.py --run-id <uuid>               [--env prod]
    python3 search_runs.py --trace-id <uuid>             [--env prod]

Options:
    --env     dev | nprd | prod   (default: nprd; dev+nprd share one instance)
    --region  usw2 | apse2 | euc1 (default: usw2)
    --mode    list | overview | feedback | tree | tools | llm | raw (default:
              overview, or list for account/user searches which match many
              conversations). tree = full nested run tree (every child run).
    --limit   max matches to return (default: 20)

Credentials resolution order: existing shell env -> this skill's .env ->
auto-fetch from AWS Secrets Manager (dev01/nprd01/prod01 agent-secrets) into
that .env (created if missing). See docs/langsmith-trace.md for the static
project-id map mirrored below.
"""
import argparse
import json
import os
import re
import subprocess
import sys

# --- static config (see docs/langsmith-trace.md; these do not change) --------
ENDPOINTS = {
    "nprd": "https://langsmith.nprd.usw2.plat.cxp.csco.cloud/api/v1",
    "prod": "https://langsmith.prod.usw2.plat.cxp.csco.cloud/api/v1",
}
# dev and nprd traces both land on the nprd instance — same credentials,
# no separate dev secret/fetch needed.
ENV_INSTANCE = {"dev": "nprd", "nprd": "nprd", "prod": "prod"}

# Same agent-secrets store query_cisco_iq_account.sh pulls BDB_* creds from,
# one per LangSmith *instance* (not per env tier — dev reuses nprd's).
LANGSMITH_SECRETS = {
    "nprd": ("cx/usw2/nprd01/configbp-ai/secrets/agent-secrets", "platform-nprd-admin"),
    "prod": ("cx/usw2/prod01/configbp-ai/secrets/agent-secrets", "platform-prod-admin"),
}
AWS_SECRETS_REGION = "us-west-2"

PROJECT_IDS = {
    "ciq-agents-dev-usw2": "f61ac999-0a80-473f-85a0-a7ffdef42ee3",
    "ciq-agents-nprd-usw2": "f6217038-b88b-4d26-9057-bd7ac54cdafd",
    "ciq-agents-nprd-apse2": "52bfc811-13b4-45d2-b894-c5dbf118f94b",
    "ciq-agents-nprd-euc1": "189787a0-bca2-41c0-8374-9edcef9a50a0",
    "ciq-agents-prod-usw2": "4bce4ab6-1a35-408b-bf0c-8da905aac00b",
    "ciq-agents-prod-apse2": "4050c6cc-6f65-4b99-aeaa-9872f6d55a4b",
    "ciq-agents-prod-euc1": "176489db-e561-4466-b59e-76786c1af36c",
}


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


# --- credentials -------------------------------------------------------------
def env_file_path():
    return os.path.join(os.path.dirname(__file__), "..", ".env")


def load_env():
    """Load KEY=VALUE pairs from the skill's .env (one dir above scripts/)."""
    env_path = env_file_path()
    if not os.path.isfile(env_path):
        return
    with open(env_path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"'))


def _fetch_secret(secret_id, profile):
    return subprocess.run(
        [
            "aws",
            "secretsmanager",
            "get-secret-value",
            "--secret-id",
            secret_id,
            "--profile",
            profile,
            "--region",
            AWS_SECRETS_REGION,
            "--query",
            "SecretString",
            "--output",
            "text",
        ],
        capture_output=True,
        text=True,
    )


def _fetch_langsmith_instance_from_aws(instance):
    """Fetch this LangSmith instance's (nprd or prod) agent-secrets and
    return its LANGSMITH_* keys, remapped to LANGSMITH_{NPRD,PROD}_*. The
    secret itself carries *generic* key names (LANGSMITH_API_KEY,
    LANGSMITH_ENDPOINT, LANGSMITH_PROJECT, ...) scoped to that AWS account —
    prefixing here is what avoids nprd/prod clobbering the same generic key
    when both are fetched in one run. dev uses the nprd instance's creds
    as-is (see ENV_INSTANCE) — there is no separate dev secret. Retries once
    via duo-sso on an auth failure (same pattern as
    query_cisco_iq_account.sh's ensure_bdb_credentials)."""
    secret_id, profile = LANGSMITH_SECRETS[instance]
    result = _fetch_secret(secret_id, profile)
    if result.returncode != 0:
        if re.search(
            r"expired|token|credentials|sso|Unauthorized|AccessDenied",
            result.stderr or "",
            re.I,
        ):
            subprocess.run(["duo-sso"], check=False)
            result = _fetch_secret(secret_id, profile)
        if result.returncode != 0:
            print(
                f"WARNING: could not fetch {secret_id} ({profile}): "
                f"{result.stderr.strip()}",
                file=sys.stderr,
            )
            return {}
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"WARNING: {secret_id} did not return JSON", file=sys.stderr)
        return {}

    prefix = instance.upper()
    out = {}
    for k, v in data.items():
        if not k.startswith("LANGSMITH_"):
            continue
        suffix = k[len("LANGSMITH_") :]
        out[f"LANGSMITH_{prefix}_{suffix}"] = str(v).strip()
    return out


def _merge_into_env_file(updates):
    """Write/update KEY=VALUE pairs in the skill's .env, preserving other
    lines, matching query_cisco_iq_account.sh's merge_bdb_into_skill_env."""
    path = env_file_path()
    existing = {}
    other_lines = []
    if os.path.isfile(path):
        with open(path) as fh:
            for raw in fh.read().splitlines():
                if not raw.strip() or raw.lstrip().startswith("#"):
                    other_lines.append(raw)
                    continue
                if "=" in raw:
                    k, v = raw.split("=", 1)
                    existing[k.strip()] = v.strip()
                else:
                    other_lines.append(raw)
    for k, v in updates.items():
        existing[k] = v

    out = list(other_lines)
    for k in sorted(existing):
        out.append(f"{k}={existing[k]}")
    with open(path, "w") as fh:
        fh.write("\n".join(out).rstrip() + "\n")
    os.chmod(path, 0o600)


def ensure_langsmith_credentials(env):
    """Auto-fetch LANGSMITH_* creds for both LangSmith instances (nprd, prod)
    from AWS Secrets Manager into the skill's .env when the requested env's
    key is missing — same auto-provision pattern as
    query_cisco_iq_account.sh's BDB creds. dev shares nprd's creds, so there
    are only two instances to fetch, not three env tiers."""
    instance = ENV_INSTANCE.get(env, env)
    prefix = instance.upper()
    if os.environ.get(f"LANGSMITH_{prefix}_API_KEY"):
        return

    print(
        f"LANGSMITH_{prefix}_API_KEY not set; fetching LangSmith credentials "
        f"from nprd/prod agent-secrets...",
        file=sys.stderr,
    )
    updates = {}
    for inst in ("nprd", "prod"):
        updates.update(_fetch_langsmith_instance_from_aws(inst))
    if not updates:
        return

    # Generic default (used when no env is specified) mirrors nprd.
    updates.setdefault(
        "LANGSMITH_ENDPOINT", updates.get("LANGSMITH_NPRD_ENDPOINT", ENDPOINTS["nprd"])
    )
    updates.setdefault("LANGSMITH_API_KEY", updates.get("LANGSMITH_NPRD_API_KEY", ""))

    _merge_into_env_file(updates)
    for k, v in updates.items():
        os.environ.setdefault(k, v)
    print(f"Updated {env_file_path()} with LangSmith credentials.", file=sys.stderr)


def make_client(env):
    """Build a LangSmith Client for the instance serving this env."""
    try:
        from langsmith import Client
    except ImportError:
        die("langsmith SDK not installed. Run: uv pip install langsmith")

    instance = ENV_INSTANCE.get(env)
    if not instance:
        die(f"Unknown env '{env}'. Choose from: {', '.join(ENV_INSTANCE)}")

    prefix = env.upper()  # DEV / NPRD / PROD
    ensure_langsmith_credentials(env)
    endpoint = os.environ.get(f"LANGSMITH_{prefix}_ENDPOINT") or ENDPOINTS[instance]
    api_key = os.environ.get(f"LANGSMITH_{prefix}_API_KEY")
    if not api_key:
        # dev falls back to the shared nprd key if a dev-specific one is absent.
        api_key = os.environ.get(f"LANGSMITH_{instance.upper()}_API_KEY")
    if not api_key:
        die(
            f"No API key for env '{env}'. Set LANGSMITH_{prefix}_API_KEY in .env "
            f"or check AWS access (platform-{env}-admin + duo-sso)."
        )

    return Client(api_url=endpoint, api_key=api_key)


def project_for(env, region):
    name = f"ciq-agents-{env}-{region}"
    pid = PROJECT_IDS.get(name)
    if not pid:
        die(f"No project id for '{name}'. Known: {', '.join(sorted(PROJECT_IDS))}")
    return name, pid


def meta(run):
    return (run.extra or {}).get("metadata", {}) or {}


# LLM runs that are guardrail/framework plumbing, not the answering agent.
GUARDRAIL_LLM_NAMES = {
    "nemo_generate_async",
    "GuardrailsLLM",
    "_CiscoAIFrameworkChatModel",
}


def llm_messages(run):
    """Return the input messages of an LLM run as [{role, content}], handling
    LangChain's list-of-list shape. System prompt(s) come first."""
    raw = (run.inputs or {}).get("messages")
    if not raw:
        return []
    seq = raw[0] if isinstance(raw, list) and raw and isinstance(raw[0], list) else raw
    out = []
    for m in seq if isinstance(seq, list) else []:
        if not isinstance(m, dict):
            continue
        mid = str(m.get("id", []))
        role = (
            "system"
            if "System" in mid
            else (
                "human"
                if "Human" in mid
                else "ai" if "AI" in mid else "tool" if "Tool" in mid else mid
            )
        )
        out.append({"role": role, "content": m.get("kwargs", {}).get("content", "")})
    return out


def llm_output_text(run):
    """Extract the assistant text from an LLM run's outputs."""
    gens = (run.outputs or {}).get("generations") or [[]]
    for g in gens[0] if gens else []:
        content = (g.get("message") or {}).get("kwargs", {}).get("content")
        if content:
            return content
    return None


# --- trace analysis ----------------------------------------------------------
def root_summary(run):
    """One-line-ish summary dict for a root run (Semantic Router / FeedbackGraph)."""
    inp = run.inputs or {}
    out = run.outputs or {}
    md = meta(run)
    question = inp.get("input") or (inp.get("payload") or {}).get("question")
    ctx = (inp.get("payload") or {}).get("context") or {}
    return {
        "run_id": str(run.id),
        "trace_id": str(run.trace_id),
        "name": run.name,
        "status": run.status,
        "start_time": str(run.start_time)[:19],
        "question": question,
        "answer": out.get("output"),
        "agent_choice": out.get("agent_choice"),
        "thread_id": md.get("thread_id"),
        "platform_account_id": md.get("platform_account_id"),
        "user_id": md.get("user_id"),
        "user_name": md.get("user_name"),
        "page_url": ctx.get("url"),
        "source": ctx.get("source"),
        "app": ctx.get("app"),
        "total_tokens": run.total_tokens,
    }


def analyze_trace(client, project_name, root):
    """Full overview of one configbp trace: routing path, tools, llm calls, errors."""
    runs = list(client.list_runs(project_name=project_name, trace_id=root.trace_id))
    runs.sort(key=lambda r: r.dotted_order or "")

    def depth(r):
        return meta(r).get("ls_run_depth")

    routing = [r.name for r in runs if depth(r) == 2]
    tools = [
        {
            "name": r.name,
            "status": r.status,
            "inputs": r.inputs,
            "outputs": r.outputs,
            "error": r.error,
        }
        for r in runs
        if r.run_type == "tool"
    ]
    llm_calls = [r for r in runs if r.run_type == "llm"]
    errors = [
        {"name": r.name, "run_type": r.run_type, "error": str(r.error)[:500]}
        for r in runs
        if r.status == "error"
    ]
    return {
        "summary": root_summary(root),
        "routing_path": routing,
        "tools_called": tools,
        "llm_call_count": len(llm_calls),
        "run_count": len(runs),
        "errors": errors,
    }


def analyze_feedback(client, project_name, root):
    """Root-cause bundle for a Q&A turn: what the user asked, what we answered,
    the answering agent's system prompt + conversation/UI context, routing, and
    errors — everything needed to judge 'missing functionality' vs a failure."""
    runs = list(client.list_runs(project_name=project_name, trace_id=root.trace_id))
    runs.sort(key=lambda r: r.dotted_order or "")
    summary = root_summary(root)

    # The answering agent's LLM call(s): llm runs that are not guardrail/framework.
    # The agent (agent/nodes/assistant.py) sends system messages in order:
    #   1) role/capabilities prompt, 2) UI context (only if present),
    #   3) conversation history (only if present). Classify by content marker
    #   rather than position, since UI context is optional.
    agents = []
    for r in runs:
        if r.run_type != "llm" or r.name in GUARDRAIL_LLM_NAMES:
            continue
        msgs = llm_messages(r)
        systems = [m["content"] for m in msgs if m["role"] == "system"]
        user_msgs = [m["content"] for m in msgs if m["role"] == "human"]

        ui_context = next(
            (s for s in systems if "Application Context(UI Context)" in str(s)), None
        )
        conversation = next(
            (s for s in systems if "Conversation History" in str(s)), None
        )
        role_prompt = next(
            (s for s in systems if s not in (ui_context, conversation)),
            None,
        )
        agents.append(
            {
                "node": r.name,
                "status": r.status,
                "system_prompt": role_prompt,
                "ui_context_present": ui_context is not None,
                "ui_context": ui_context,
                "conversation_history": conversation,
                "user_message": user_msgs[-1] if user_msgs else None,
                "answer": llm_output_text(r),
            }
        )

    return {
        "summary": summary,
        "ui_context": (root.inputs or {}).get("payload", {}).get("context"),
        "routing_path": [r.name for r in runs if meta(r).get("ls_run_depth") == 2],
        "answering_agents": agents,
        "errors": [
            {"name": r.name, "error": str(r.error)[:500]}
            for r in runs
            if r.status == "error"
        ],
    }


def build_tree(client, project_name, root):
    """Full nested run tree for one trace: EVERY child run, parent->child, with
    metadata + full inputs/outputs per node. Siblings ordered by dotted_order."""
    runs = list(client.list_runs(project_name=project_name, trace_id=root.trace_id))
    runs.sort(key=lambda r: r.dotted_order or "")

    def duration_ms(r):
        if not r.start_time or not r.end_time:
            return None
        return round((r.end_time - r.start_time).total_seconds() * 1000)

    def node(r):
        return {
            "id": str(r.id),
            "name": r.name,
            "run_type": r.run_type,
            "status": r.status,
            "depth": meta(r).get("ls_run_depth"),
            "duration_ms": duration_ms(r),
            "tokens": {
                "total": r.total_tokens,
                "prompt": r.prompt_tokens,
                "completion": r.completion_tokens,
            },
            "error": r.error,
            "inputs": r.inputs,
            "outputs": r.outputs,
            "children": [],
        }

    nodes = {str(r.id): node(r) for r in runs}
    forest = []
    for r in runs:
        n = nodes[str(r.id)]
        parent = nodes.get(str(r.parent_run_id)) if r.parent_run_id else None
        (parent["children"] if parent else forest).append(n)

    # Normally exactly one root (== the trace root); fall back to a synthetic
    # wrapper if the trace somehow has multiple top-level runs.
    tree = forest[0] if len(forest) == 1 else {"name": "(trace)", "children": forest}
    return {"summary": root_summary(root), "run_count": len(runs), "tree": tree}


def find_roots_by_metadata(client, project_name, key, value, is_root, limit):
    """Search runs by a metadata key/value. For child-level keys (account/user)
    pass is_root=False, then dedupe to distinct traces and fetch their roots."""
    flt = f'and(eq(metadata_key, "{key}"), eq(metadata_value, "{value}"))'
    hits = list(
        client.list_runs(
            project_name=project_name, filter=flt, is_root=is_root, limit=limit * 10
        )
    )
    if is_root:
        return hits[:limit]
    # child hits: dedupe by trace, fetch each root
    seen, roots = set(), []
    for h in hits:
        if h.trace_id in seen:
            continue
        seen.add(h.trace_id)
        try:
            roots.append(client.read_run(str(h.trace_id)))
        except Exception:
            continue
        if len(roots) >= limit:
            break
    return roots


# --- main --------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(add_help=True, description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--thread-id")
    g.add_argument("--platform-account-id")
    g.add_argument("--user-id")
    g.add_argument("--run-id")
    g.add_argument("--trace-id")
    p.add_argument("--env", default="nprd", choices=list(ENV_INSTANCE))
    p.add_argument("--region", default="usw2", choices=["usw2", "apse2", "euc1"])
    p.add_argument(
        "--mode",
        default=None,
        choices=["list", "overview", "feedback", "tree", "tools", "llm", "raw"],
    )
    p.add_argument("--limit", type=int, default=20)
    args = p.parse_args()

    load_env()
    client = make_client(args.env)
    project_name, _ = project_for(args.env, args.region)

    # Resolve target root run(s) from whichever filter was given.
    if args.run_id or args.trace_id:
        rid = args.run_id or args.trace_id
        roots = [client.read_run(rid)]
        default_mode = "overview"
    elif args.thread_id:
        roots = find_roots_by_metadata(
            client, project_name, "thread_id", args.thread_id, True, args.limit
        )
        default_mode = "list" if len(roots) > 1 else "overview"
    else:
        key = "platform_account_id" if args.platform_account_id else "user_id"
        val = args.platform_account_id or args.user_id
        roots = find_roots_by_metadata(
            client, project_name, key, val, False, args.limit
        )
        default_mode = "list"

    mode = args.mode or default_mode
    if not roots:
        print(json.dumps({"project": project_name, "matches": 0, "runs": []}, indent=2))
        return

    if mode == "list":
        out = {
            "project": project_name,
            "matches": len(roots),
            "runs": [root_summary(r) for r in roots],
        }
    elif mode == "raw":
        out = {"project": project_name, "runs": [r.dict() for r in roots]}
    elif mode == "tools":
        out = {
            "project": project_name,
            "traces": [
                {
                    "run_id": str(r.id),
                    "question": root_summary(r)["question"],
                    "tools_called": analyze_trace(client, project_name, r)[
                        "tools_called"
                    ],
                }
                for r in roots
            ],
        }
    elif mode == "llm":
        out = {"project": project_name, "traces": []}
        for r in roots:
            runs = list(
                client.list_runs(project_name=project_name, trace_id=r.trace_id)
            )
            llm = [
                {
                    "name": x.name,
                    "inputs": x.inputs,
                    "outputs": x.outputs,
                    "status": x.status,
                }
                for x in sorted(runs, key=lambda z: z.dotted_order or "")
                if x.run_type == "llm"
            ]
            out["traces"].append({"run_id": str(r.id), "llm_calls": llm})
    elif mode == "tree":
        out = {
            "project": project_name,
            "traces": [build_tree(client, project_name, r) for r in roots],
        }
    elif mode == "feedback":
        # Only the Q&A roots matter for feedback analysis; skip FeedbackGraph
        # (the thumbs-up/down event itself, which carries no question).
        qa = [r for r in roots if (r.inputs or {}).get("input")] or roots
        out = {
            "project": project_name,
            "turns": [analyze_feedback(client, project_name, r) for r in qa],
        }
    else:  # overview
        out = {
            "project": project_name,
            "traces": [analyze_trace(client, project_name, r) for r in roots],
        }

    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
