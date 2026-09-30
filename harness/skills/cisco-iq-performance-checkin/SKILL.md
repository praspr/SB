---
name: cisco-iq-performance-checkin
description: >-
  Drafts Cisco weekly Check-ins, SMART performance goals, and Guiding
  Principles copy from CIQ CHANGELOG evidence. Use when the user asks for a
  check-in, "one improvement last week", Business Outcome goal, CSDL or
  threat-modeling goal, performance review wording, or third-person check-in
  copy. Also trigger on Check-in Guide, Guiding Principles, or "under 500
  chars".
---

# Cisco IQ Performance Check-in

Ground every answer in **this repo's evidence**. Do not invent work.

**Employee:** Prasad (JIRA: PRASAD P R). Default voice is first person ("I"). Switch to third person ("Prasad" / "He") only when asked.

## When to use

- Weekly Check-in / "one improvement last week" / what did you learn
- SMART goal (Business Outcome, CSDL, technical execution)
- High-level rewrite, character cap, or third-person rewrite of prior copy

Do **not** use for standup, JIRA status, or engineering design docs. Those are different rituals.

## Evidence first

1. Read `CHANGELOG.md` at repo root. "Last week" is the previous calendar week relative to **today's date in user_info** (Mon–Sun). Exclude today if today is Monday and that week's work has not started.
2. Skim `REPO_LANDMARK.md` for active initiatives (Priority Bugs AI, ConfigBP, BAQS, CSDL).
3. If a ticket is named, read `docs/jira/tickets/<KEY>.md`.
4. Check prior check-in drafts in this chat and in `CHANGELOG.md` (`Drafted weekly check-in`). **Do not repeat last week's story.**

Pick **one** improvement. Prefer customer impact over internal plumbing.

## Weekly Check-in — "one improvement"

Shape: **what changed for customers/team + what was learned.** Outcome language only.

| Include | Exclude |
|---------|---------|
| Customer or teammate effect | Table names, join keys, status enums, header names |
| One learning from the work | PR numbers, pod names, LangSmith IDs, eval fractions |
| Distinct story from prior week | Stacked bug lists, SQL, ticket IDs in the paste |

If the form has a character cap, default **under 500 characters** (count before sending). High-level means no implementation details even when the user does not mention a cap.

### Voice

**First person (default):**
> Last week I [customer outcome]. I learned [principle, not a technique name].

**Third person (on request):**
> Last week Prasad [customer outcome]. He learned [principle].

### Guiding Principles (optional, only if the form asks)

Map the same story; do not add a second accomplishment.

| Principle | Signal in the work |
|-----------|-------------------|
| Think Really Big | Sequenced delivery, de-risked scale (e.g. threat model before NPRD) |
| Play to Win | Owned a customer-facing defect through to a usable path |
| Drive Durable Growth | Tenant isolation, answers matching the UI, platform path customers actually use |

## SMART goals

A goal is a 1–2 quarter **outcome**, not a task list. Fill Specific, Measurable, Attainable, Relevant, Timebound. Lead with customer/business result.

**Business Outcome pattern:** what customers can do, success measures (deployed, eval pass rate, defect bar), named dependencies, end-of-quarter date.

**CSDL / threat-modeling pattern:** structured AITM + STO sign-off for Assessments **message processing, ETL, and assessment read paths**; living threat-model doc; High/Critical items mitigated or accepted. Follow the Semantic Router model at `cvi-ai-a2a/docs/threat-model/semantic-router-threat-model.md` (structure only — do not copy that service's risks).

Offer a **short form** for the review portal and a **longer SMART table** only if the user wants it.

## After drafting

Append one line to root `CHANGELOG.md` under today's date:

```
- **Drafted** weekly check-in answer (under 500 chars, high-level[, third person]): <one-line gist> — *`docs` / performance*
```

## Examples

See [examples.md](examples.md) for paste-ready copy from prior weeks. Reuse the **shape**, never the same improvement twice.
