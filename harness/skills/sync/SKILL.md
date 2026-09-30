---
name: sync
description: Refreshes local signal adapters and reports synchronization state when source data may be stale.
---

# Sync

## Allowed tools
- `sync_adapters`
- `sync_status`

## Procedure
1. Use `sync_status` to inspect source freshness and prior errors.
2. Run `sync_adapters` only for the local sources that need refreshing.
3. Report per-source counts, timestamps, and errors without hiding partial failures.
4. Do not turn synchronization into a remote write.
