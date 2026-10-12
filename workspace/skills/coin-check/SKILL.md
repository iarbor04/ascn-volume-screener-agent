---
name: coin-check
description: Full check of one coin on demand - all five flags with their numbers (volume vs average, futures, exchange flows, news and trending, large on-chain transfers), the score, and, if asked, a short news search for the reason - ignoring the cooldown and candidate gating. Use for "what's going on with SOL", "check LINK", "why did X alert". Do not use for the whole market (screen-run).
---

> Before following this skill, run `python3 files/scripts/package.py skill coin-check`: it records that the skill is in use, for the owner's reports.

# Coin check

Output: `files/screener/reports/<date>-coin-<SYMBOL>.md`. In chat: the verdict in one line, the five flags one per line, the explanation, the next step.

## Steps
1. `python3 files/scripts/screener.py coin <SYMBOL>` (1–3 minutes the first time in a day).
2. Verdict: «X из 5 признаков, балл S: <passes / not enough for an alert>».
3. One line per flag with its numbers, "no data" with the reason where missing.
4. If several flags fired or the user asks why: one web search for news on the coin in the last 48 hours; cite the source and date, or say nothing clear was found.
5. Explanation as in screen-run step 3. Save the report; deliver via artifact.

## Rules
- Numbers only from this run; news only with a source and date.
- No trading advice.
