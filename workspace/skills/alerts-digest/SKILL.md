---
name: alerts-digest
description: Summarizes the screener's alerts over a period and checks what happened after each one - price at the alert vs now, which flags fired, repeat coins - so the user can judge whether the screener catches real moves and whether to tune it. Use for "weekly summary", "how good are the alerts", "what did you catch this week", "history". Do not use for a new screen (screen-run).
---

> Before following this skill, run `python3 files/scripts/package.py skill alerts-digest`: it records that the skill is in use, for the owner's reports.

# Alerts digest

Output: `files/screener/reports/<date>-digest.md`. In chat: count, the biggest moves after alerts, what to tune.

## Steps
1. `python3 files/scripts/screener.py followup --days <7 or what the user asked>`.
2. If empty: say there were no alerts and offer to soften the thresholds (scoring-setup) or to show the closest coins with a manual run.
3. Otherwise: number of alerts, the median move after them, up vs down, the 3 largest moves, coins that alerted repeatedly, which flag combinations appeared most.
4. Suggest one tuning step if the data supports it (e.g. many alerts with tiny moves → stricter `min_flags` or higher `volume_ratio`), as a proposal.
5. Save the report; deliver via artifact. A weekly digest on schedule only after an explicit yes (one cron task running this skill).

## Rules
- A move after an alert either way means it caught something; never present alerts as a profitable strategy or compute "returns if you had bought".
