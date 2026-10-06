# sb launchd jobs

Three plists live here:

| Plist | Label | Purpose |
|---|---|---|
| `com.praspr.sb.plist` | `com.praspr.sb` | The unified sb-core MCP process (uvicorn, `:8787`). Load-at-boot, keep-alive. Also serves the built dashboard same-origin at `/_ui` (run `npm run build` in `sb/web` once so `web/dist` exists). |
| `com.praspr.sb-morning-open.plist` | `com.praspr.sb-morning-open` | Opens the dashboard once per day (morning). Never keeps the process alive. |
| `com.praspr.sb-scheduler.plist` | `com.praspr.sb-scheduler` | Calls `run_due_schedules` over MCP every 5 minutes so scheduled rituals fire without a foreground process. |

## Install

```bash
cp services/core/launchd/com.praspr.sb.plist ~/Library/LaunchAgents/
cp services/core/launchd/com.praspr.sb-morning-open.plist ~/Library/LaunchAgents/
cp services/core/launchd/com.praspr.sb-scheduler.plist ~/Library/LaunchAgents/

launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.praspr.sb.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.praspr.sb-morning-open.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.praspr.sb-scheduler.plist
```

## Bootout / remove

```bash
launchctl bootout gui/$(id -u)/com.praspr.sb-scheduler || true
launchctl bootout gui/$(id -u)/com.praspr.sb-morning-open || true
launchctl bootout gui/$(id -u)/com.praspr.sb || true

rm -f ~/Library/LaunchAgents/com.praspr.sb-scheduler.plist
rm -f ~/Library/LaunchAgents/com.praspr.sb-morning-open.plist
rm -f ~/Library/LaunchAgents/com.praspr.sb.plist
```

## Restart / kickstart after a code change

```bash
launchctl kickstart -k gui/$(id -u)/com.praspr.sb
```

The morning-open and scheduler jobs do not need a kickstart after a code
change — they only invoke `curl`/`open`, not the Python process directly.

## Notes

- `com.praspr.sb-morning-open` fires once per calendar day at 08:30 local
  time (`StartCalendarInterval`). It opens the dashboard: prefer the
  Vite dev server (`http://127.0.0.1:5173/_ui/`) when reachable, otherwise
  the same-origin production UI served by sb-core at
  `http://127.0.0.1:8787/_ui/` (available whenever `web/dist` is built).
  `RunAtLoad`/`KeepAlive` are both false — this is a fire-once-a-day
  convenience, not a service.
- `com.praspr.sb-scheduler` runs every 300 seconds (`StartInterval`) and
  POSTs a `run_due_schedules` MCP tool call to sb-core. If sb-core is not
  up, the `curl` call fails silently (`|| true`) and the next interval
  retries — no error surfaces to launchd, and `KeepAlive` stays false since
  this is a one-shot poke, not a long-running process.
- Logs: `/tmp/sb-morning-open.{out,err}.log` and
  `/tmp/sb-scheduler.{out,err}.log`, alongside the core service's
  `/tmp/sb.{out,err}.log`.
