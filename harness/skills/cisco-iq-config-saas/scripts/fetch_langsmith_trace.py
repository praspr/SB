#!/usr/bin/env python3
"""Fetch and display a LangSmith trace as structured JSON.

Usage:
    python3 fetch_trace.py <trace_url_or_share_token> [--mode overview|full|messages|tokens|tools|raw]

Modes:
    overview   Summary metadata, run tree, and token totals (default)
    full       Everything: overview + messages + tool definitions + raw outputs
    messages   Conversation message sequence only
    tokens     Per-step token breakdown
    tools      Available tool definitions
    raw        Raw JSON dump of the root run

Environment:
    LANGSMITH_API_KEY    API key (optional for public traces)
    LANGSMITH_ENDPOINT   API base URL fallback when passing a bare token

Examples:
    python3 fetch_trace.py https://langsmith.prod.usw2.plat.cxp.csco.cloud/public/abcd1234-.../r
    python3 fetch_trace.py abcd1234-... --mode messages
    python3 fetch_trace.py https://smith.langchain.com/public/abcd1234-.../r --mode full
"""
import json, sys, re, urllib.request, os
from datetime import datetime

API_KEY = os.environ.get("LANGSMITH_API_KEY", "")


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------
def parse_args():
    args = sys.argv[1:]
    if not args:
        print(__doc__.strip())
        sys.exit(1)

    raw = args[0].strip().rstrip("/")
    mode = "overview"
    if "--mode" in args:
        idx = args.index("--mode")
        if idx + 1 < len(args):
            mode = args[idx + 1]

    # Extract base URL + share token from full URL
    m = re.match(r"(https?://[^/]+)/public/([0-9a-f-]+)", raw)
    if m:
        base = m.group(1) + "/api/v1"
        token = m.group(2)
    else:
        endpoint = os.environ.get(
            "LANGSMITH_ENDPOINT",
            "https://langsmith.prod.usw2.plat.cxp.csco.cloud/api/v1",
        )
        base = endpoint.rstrip("/")
        token = raw

    return base, token, mode


BASE, SHARE_TOKEN, MODE = parse_args()


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def fetch(url):
    headers = {}
    if API_KEY:
        headers["x-api-key"] = API_KEY
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def seconds_between(start, end):
    if not (start and end):
        return None
    try:
        s = datetime.fromisoformat(start.replace("Z", "+00:00"))
        e = datetime.fromisoformat(end.replace("Z", "+00:00"))
        return (e - s).total_seconds()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Extractors
# ---------------------------------------------------------------------------
def extract_metadata(root):
    extra = root.get("extra", {})
    metadata = extra.get("metadata", {})
    invocation = extra.get("invocation_params", {})
    start = root.get("start_time", "")
    end = root.get("end_time", "")
    dur = seconds_between(start, end)

    return {
        "model": metadata.get("ls_model_name", invocation.get("model", "N/A")),
        "provider": metadata.get("ls_provider", "N/A"),
        "temperature": invocation.get("temperature", "N/A"),
        "trace_id": root.get("trace_id", "N/A"),
        "run_id": str(root.get("id", "N/A")),
        "parent_run_id": root.get("parent_run_id"),
        "status": root.get("status", "N/A"),
        "run_type": root.get("run_type", "N/A"),
        "name": root.get("name", "N/A"),
        "tags": root.get("tags", []),
        "start_time": start,
        "end_time": end,
        "duration_seconds": dur,
        "total_tokens": root.get("total_tokens"),
        "prompt_tokens": root.get("prompt_tokens"),
        "completion_tokens": root.get("completion_tokens"),
        "total_cost": root.get("total_cost"),
        "first_token_time": root.get("first_token_time"),
    }


def extract_messages(root):
    """Parse the input message array into a clean list."""
    msgs_raw = root.get("inputs", {}).get("messages", [[]])
    if not msgs_raw or not msgs_raw[0]:
        return []

    messages = []
    for msg in msgs_raw[0]:
        kwargs = msg.get("kwargs", {})
        msg_id = str(msg.get("id", []))

        if "SystemMessage" in msg_id:
            messages.append(
                {
                    "role": "system",
                    "content": kwargs.get("content", ""),
                }
            )
        elif "HumanMessage" in msg_id:
            messages.append(
                {
                    "role": "human",
                    "content": kwargs.get("content", ""),
                }
            )
        elif "AIMessage" in msg_id:
            rm = kwargs.get("response_metadata", {})
            tu = rm.get("token_usage", {})
            entry = {
                "role": "ai",
                "content": kwargs.get("content", ""),
                "finish_reason": rm.get("finish_reason"),
                "model": rm.get("model_name"),
                "token_usage": {
                    "prompt_tokens": tu.get("prompt_tokens"),
                    "completion_tokens": tu.get("completion_tokens"),
                    "total_tokens": tu.get("total_tokens"),
                    "cached_tokens": (tu.get("prompt_tokens_details") or {}).get(
                        "cached_tokens", 0
                    ),
                    "reasoning_tokens": (tu.get("completion_tokens_details") or {}).get(
                        "reasoning_tokens", 0
                    ),
                },
                "tool_calls": [],
            }
            for tc in kwargs.get("tool_calls", []):
                entry["tool_calls"].append(
                    {
                        "name": tc.get("name"),
                        "args": tc.get("args", {}),
                        "id": tc.get("id"),
                    }
                )
            messages.append(entry)
        elif "ToolMessage" in msg_id:
            messages.append(
                {
                    "role": "tool",
                    "name": kwargs.get("name", ""),
                    "status": kwargs.get("status", ""),
                    "content": kwargs.get("content", ""),
                    "tool_call_id": kwargs.get("tool_call_id", ""),
                }
            )

    return messages


def extract_output(root):
    """Parse the LLM output from this run step."""
    gens = (root.get("outputs") or {}).get("generations", [[]])
    result = {
        "content": "",
        "tool_calls": [],
        "llm_output": {},
    }
    for g in gens[0] if gens else []:
        mk = g.get("message", {}).get("kwargs", {})
        if mk.get("content"):
            result["content"] = mk["content"]
        for tc in mk.get("tool_calls", []):
            result["tool_calls"].append(
                {
                    "name": tc.get("name"),
                    "args": tc.get("args", {}),
                    "id": tc.get("id"),
                }
            )

    llm_output = (root.get("outputs") or {}).get("llm_output", {})
    result["llm_output"] = llm_output
    return result


def extract_token_summary(root, messages):
    """Build per-step and cumulative token counts."""
    steps = []
    total = {"prompt": 0, "completion": 0, "cached": 0, "reasoning": 0, "total": 0}

    for msg in messages:
        if msg.get("role") == "ai" and msg.get("token_usage"):
            tu = msg["token_usage"]
            step = {
                "prompt_tokens": tu.get("prompt_tokens", 0),
                "completion_tokens": tu.get("completion_tokens", 0),
                "cached_tokens": tu.get("cached_tokens", 0),
                "reasoning_tokens": tu.get("reasoning_tokens", 0),
                "total_tokens": tu.get("total_tokens", 0),
            }
            steps.append(step)
            total["prompt"] += step["prompt_tokens"]
            total["completion"] += step["completion_tokens"]
            total["cached"] += step["cached_tokens"]
            total["reasoning"] += step["reasoning_tokens"]
            total["total"] += step["total_tokens"]

    # Add the final step from this run's output
    llm_output = (root.get("outputs") or {}).get("llm_output", {})
    tu = llm_output.get("token_usage", {})
    if tu:
        step = {
            "prompt_tokens": tu.get("prompt_tokens", 0),
            "completion_tokens": tu.get("completion_tokens", 0),
            "cached_tokens": (tu.get("prompt_tokens_details") or {}).get(
                "cached_tokens", 0
            ),
            "reasoning_tokens": (tu.get("completion_tokens_details") or {}).get(
                "reasoning_tokens", 0
            ),
            "total_tokens": tu.get("total_tokens", 0),
            "is_current_step": True,
        }
        steps.append(step)
        total["prompt"] += step["prompt_tokens"]
        total["completion"] += step["completion_tokens"]
        total["cached"] += step["cached_tokens"]
        total["reasoning"] += step["reasoning_tokens"]
        total["total"] += step["total_tokens"]

    return {"steps": steps, "total": total}


def extract_tools(root):
    """Extract available tool definitions from invocation params."""
    tools_raw = root.get("extra", {}).get("invocation_params", {}).get("tools", [])
    tools = []
    for t in tools_raw:
        fn = t.get("function", {})
        params = fn.get("parameters", {}).get("properties", {})
        tools.append(
            {
                "name": fn.get("name", ""),
                "description": fn.get("description", ""),
                "parameters": list(params.keys()),
            }
        )
    return tools


def extract_run_tree(root):
    """Build run tree with children."""
    node = {
        "name": root.get("name", "?"),
        "run_type": root.get("run_type", "?"),
        "status": root.get("status", "?"),
        "duration_seconds": seconds_between(
            root.get("start_time"), root.get("end_time")
        ),
        "total_tokens": root.get("total_tokens"),
        "error": root.get("error"),
        "children": [],
    }

    child_ids = root.get("direct_child_run_ids") or root.get("child_run_ids") or []
    for cid in child_ids:
        try:
            child = fetch(f"{BASE}/public/{SHARE_TOKEN}/run/{cid}")
            node["children"].append(extract_run_tree(child))
        except Exception as e:
            node["children"].append({"error": f"Could not fetch {cid}: {e}"})

    return node


# ---------------------------------------------------------------------------
# Output modes
# ---------------------------------------------------------------------------
def mode_overview(root):
    meta = extract_metadata(root)
    messages = extract_messages(root)
    output = extract_output(root)
    tokens = extract_token_summary(root, messages)
    run_tree = extract_run_tree(root)

    return json.dumps(
        {
            "metadata": meta,
            "run_tree": run_tree,
            "inputs_preview": root.get("inputs_preview", ""),
            "output": {
                "content": output["content"][:3000],
                "tool_calls": output["tool_calls"],
            },
            "token_summary": tokens,
            "message_count": len(messages),
            "error_messages": [
                m
                for m in messages
                if m.get("role") == "tool" and m.get("status") == "error"
            ],
        },
        indent=2,
        default=str,
    )


def mode_full(root):
    meta = extract_metadata(root)
    messages = extract_messages(root)
    output = extract_output(root)
    tokens = extract_token_summary(root, messages)
    tools = extract_tools(root)
    run_tree = extract_run_tree(root)

    return json.dumps(
        {
            "metadata": meta,
            "run_tree": run_tree,
            "messages": messages,
            "output": output,
            "token_summary": tokens,
            "tools": tools,
        },
        indent=2,
        default=str,
    )


def mode_messages(root):
    messages = extract_messages(root)
    return json.dumps({"messages": messages}, indent=2, default=str)


def mode_tokens(root):
    messages = extract_messages(root)
    tokens = extract_token_summary(root, messages)
    return json.dumps(tokens, indent=2, default=str)


def mode_tools(root):
    tools = extract_tools(root)
    return json.dumps({"tools": tools}, indent=2, default=str)


def mode_raw(root):
    return json.dumps(root, indent=2, default=str)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
root = fetch(f"{BASE}/public/{SHARE_TOKEN}/run")

modes = {
    "overview": mode_overview,
    "full": mode_full,
    "messages": mode_messages,
    "tokens": mode_tokens,
    "tools": mode_tools,
    "raw": mode_raw,
}

handler = modes.get(MODE)
if not handler:
    print(
        f"Unknown mode: {MODE}. Choose from: {', '.join(modes.keys())}", file=sys.stderr
    )
    sys.exit(1)

print(handler(root))
