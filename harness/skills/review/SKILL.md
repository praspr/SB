---
name: review
description: Reviews pending local proposals when approving or rejecting suggested follow-up actions.
---

# Review

## Allowed tools
- `list_proposals`
- `approve_proposal`
- `reject_proposal`

## Procedure
1. Use `list_proposals` to inspect pending proposals and their evidence.
2. Present impact and uncertainty before requesting an approval decision.
3. Call `approve_proposal` or `reject_proposal` only after the user identifies the proposal and decision.
4. Approval records consent for the proposal; it does not authorize an Atlassian write.
