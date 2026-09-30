# cxdocs-cli (CX Platform Docs / Cisco IQ documentation / IQ docs)

Fetch a `cxdocs.cisco.com` page (CX Platform Docs, Cisco IQ documentation,
IQ docs, cxdocs) as Markdown using the internal `cxdocs-cli` tool
(`github.com/CXEPI/cxdocs-cli`), without a browser.

## What it's for

`cxdocs.cisco.com` is behind Cisco Duo SSO. `cxdocs-cli` authenticates once
via a real browser (Duo push), stores the session cookie in the OS keyring,
and then fetches any page as clean Markdown through that cookie — no repeat
SSO per page, no scraping the rendered DOM by hand.

## Prerequisites

- `uv` on `PATH` (installs/manages `cxdocs-cli` itself — see
  https://docs.astral.sh/uv/ if missing).
- Python 3.13+ (pulled in automatically by `uv tool install`).
- A `cxdocs-cli login`: opens a Chrome window, completes Cisco Duo SSO, and
  stores the session cookie in the OS keyring (service
  `cisco-browser-sessions`), valid for ~8 hours
  (`CXDOCS_SESSION_TIMEOUT_HOURS`). **The agent may run this itself** — run
  it bare (`cxdocs-cli login`, no absolute path) and in the foreground, not
  backgrounded. It reliably completes on its own within seconds when run
  this way. If it hangs beyond ~45-60s with no "Session captured
  successfully!" line, fall back to asking the user to run it themselves.
  See "cxdocs-cli agent behavior" in `SKILL.md`.

## Finding the right URL when you don't have one

Most of the time you won't have a direct `cxdocs.cisco.com` URL. Use
`scripts/cxdocs.sh search` first:

```bash
bash "$SKILL_DIR/scripts/cxdocs.sh" search "table indexing"
bash "$SKILL_DIR/scripts/cxdocs.sh" search "event driven etl" --limit 5
```

Prints `Title -- URL` per match, ranked by title matches first, then
text-body matches. Feed a result's URL into `cxdocs.sh fetch`.

How it works: the site is mkdocs-material, which ships a full-text search
index at `/search/search_index.json` (same SSO session as page fetches).
The script fetches that index once, caches it at
`$SKILL_DIR/.cache/cxdocs/search_index.json` for
`CXDOCS_SEARCH_CACHE_TTL_SECONDS` (default 1 day — pass `--refresh` to
force a re-fetch sooner), and greps titles/text locally against your query
terms. This is why it fetches the index via `cxdocs-cli`'s own auth/client
modules directly (`uv tool run --from cxdocs-cli python3 -c ...`) rather
than through `cxdocs-cli fetch`: `fetch` always runs its response through
`html2text` (built for HTML pages), which mangles the JSON escape
sequences in the search index and makes it unparseable. Going straight to
`CxDocsClient.get()` (the same call `fetch` makes internally, one step
before its markdown conversion) gets the raw JSON.

Same "no valid session" behavior as `cxdocs.sh fetch` applies here — if the
session is missing/expired, try `cxdocs-cli login` (bare, foreground)
yourself first; fall back to the user only if it hangs.

## Fetching a page

`scripts/cxdocs.sh fetch` wraps install-if-missing + the `cxdocs-cli fetch` call:

```bash
bash "$SKILL_DIR/scripts/cxdocs.sh" fetch https://cxdocs.cisco.com/getting-started/            # full page
bash "$SKILL_DIR/scripts/cxdocs.sh" fetch https://cxdocs.cisco.com/getting-started/ --body      # article only
bash "$SKILL_DIR/scripts/cxdocs.sh" fetch https://cxdocs.cisco.com/getting-started/ --nav       # sidebar link list
```

- `--full` (default) — entire page as Markdown.
- `--body` — main article content only (nav/header/footer stripped). Use
  this when summarizing or quoting a doc's content.
- `--nav` — sidebar/navigation links as a Markdown bullet list. Use this to
  discover related/child pages before fetching them.

Both subcommands auto-install `cxdocs-cli` the same way. If it isn't
installed yet, the wrapper runs `uv tool install
git+ssh://git@<host>/CXEPI/cxdocs-cli.git` automatically, and on Linux/WSL
also runs `uv tool run --from cxdocs-cli playwright install --with-deps
chromium` once (macOS/Windows use the system Chrome browser for `login`, no
extra install needed).

`<host>` is `github.com` by default, but if `~/.ssh/config` defines a `Host`
alias whose `HostName` is `github.com` and whose alias name contains `cxepi`
(case-insensitive — e.g. `Host github-cxepi`), the wrapper uses that alias
instead. This matters on machines with multiple GitHub SSH identities, where
plain `git@github.com` may pick the wrong key and fail to reach CXEPI's
private repo. Override with `CXDOCS_GIT_SSH_HOST=<alias>` (or set
`CXDOCS_INSTALL_SOURCE=<full-git+ssh-url>` to bypass detection entirely) if
the auto-detected alias is still wrong.

If no valid session exists (never logged in, or the ~8h session expired),
the wrapper's `cxdocs-cli fetch` call fails and surfaces `cxdocs-cli`'s own
message. Run `cxdocs-cli login` (bare command, foreground, no absolute
path, no `&`) yourself, wait ~45-60s for "Session captured successfully!",
then retry the fetch. Only ask the user to run `login` themselves if it's
still hanging after that — a real fresh Duo push tap that this run can't
surface to you.

## Escape hatch

The wrapper only exposes `--full`/`--body`/`--nav`. If a workflow needs
something else `cxdocs-cli` supports directly (e.g. `cxdocs-cli logout` to
clear a stale session, or `cxdocs-cli --debug fetch ...` for troubleshooting),
the agent is free to call `cxdocs-cli` directly rather than being limited to
the wrapper's flags.

## Notes

- `cxdocs-cli` is an internal Cisco (CXEPI org) tool distributed via
  `git+ssh` / an internal Artifactory index — no public license, no PyPI
  install. It is not bundled into this skill; the wrapper installs it via
  `uv tool install` on first use.
- Session storage is OS-keyring based, not a plaintext file — nothing to
  clean up or treat as a secret on disk beyond the keyring entry itself.
