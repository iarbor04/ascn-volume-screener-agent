---
name: scoring-setup
description: Shows and changes the screener's thresholds and weights - how many flags must match, the minimum score, weights per flag, volume multiple and z-score, futures and flow thresholds, cooldown, number of coins, minimum market cap, excluded coins - and explains in plain words what each change will do to the number of alerts. Use for "too many alerts", "too few", "make it stricter", "ignore news", "add/remove a coin", "show settings". Do not use for running the screen (screen-run).
---

> Before following this skill, run `python3 files/scripts/package.py skill scoring-setup`: it records that the skill is in use, for the owner's reports.

# Scoring setup

Output: `files/screener/config.json` (via the script). In chat: what changed, before → after, and the expected effect.

## Steps
1. `python3 files/scripts/screener.py config show`.
2. Map the request to keys (knowledge/scoring.md has the full list and defaults):
   - stricter / softer → `min_flags`, `min_score`; "volume not required" → `require_volume false`;
   - flag importance → `weights.volume|derivs|flow|social|onchain` (0 turns a flag off);
   - volume sensitivity → `volume_ratio`, `volume_z`; futures → `oi_change_pct`, `funding_abs_pct`, `long_short_high`, `long_short_low`; flows → `flow_pct`, `flow_z`; news → `news_ratio`, `trending_counts`; transfers → `onchain_usd`, `onchain_min_count`;
   - universe → `top_n`, `min_market_cap`, `exclude_symbols` (comma list replaces the whole list: read it first and add to it);
   - repeats → `cooldown_hours`.
3. Before changing, say the effect in one line (e.g. «4 из 5 — алертов станет заметно меньше, останутся только самые сильные совпадения»). If the user asked plainly, apply; if the request is vague, propose one concrete change and wait for a yes.
4. `python3 files/scripts/screener.py config set <key> <value>`; show before → after. `config reset` only on an explicit request.
5. Offer a manual run to see the effect.

## Rules
- Change only what was asked. Note the change with the date in the profile.
