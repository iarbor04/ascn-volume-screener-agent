---
name: screen-run
description: Runs the anomalous-volume screen over the top coins, scores five flags per coin (volume spike, futures, exchange inflow/outflow, news and trending, large on-chain transfers), and for every coin that passes the threshold writes a short explanation of what happened and why it is interesting, from the numbers only. Use for "run the screen", "anything unusual now?", and for every scheduled check. Do not use for one coin (coin-check) or to change thresholds (scoring-setup).
---

> Before following this skill, run `python3 files/scripts/package.py skill screen-run`: it records that the skill is in use, for the owner's reports.

# Screen run

Output: `files/screener/reports/<date>-screen-<HHMM>.md` when there are alerts or on manual runs. In chat: one block per alert, or one line «тихо» on a manual run, nothing at all on a quiet scheduled run.

## Steps

### 1. Run
`python3 files/scripts/screener.py run` (takes 2–10 minutes; the first run of the day is the slowest). On a manual request say once: «Проверяю топ монет, это займёт несколько минут.»

### 2. Check the sources
Read `sources`: which venue gave volume and futures, which exchanges' reserves were read, and `errors`. If a source failed, its flag is "no data" and is not counted; mention it in one line in the report (and in chat only if volume or futures are missing).

### 3. Explain each alert (from the table, never from memory)
For every item in `alerts`, write 3–5 lines:
1. **What:** the coin, price move in 24 h, volume vs the 30-day average (ratio and how unusual).
2. **What else lit up:** each fired flag with its number: futures (open-interest change, funding, long/short, and the `regime` in plain words), exchange flow (direction and size; inflow = coins going to exchanges, often before selling; outflow = coins leaving, often to hold), news and trending (rank, news ratio), large transfers (count, sum, to or from exchanges).
3. **Why it is interesting:** one line combining them, e.g. «объём вырос в 5 раз при почти неподвижной цене и притоке на биржи: кто-то крупно торгует, стоит смотреть».
4. **Caveat in one line:** data gaps (`no_data`), a single-exchange volume source, or "anomaly, not a direction".
Use knowledge/reading-signals.md for the wording of combinations.

### 4. Near misses
On manual runs, list `near` (one flag short) in one line each, and `top_volume` top 5 if there are no alerts.

### 5. Report
Save the report: run time, sources and errors, every alert with its full table (all numbers from the run), the explanations, near misses, top volume. Deliver via artifact on manual runs; on scheduled runs only when there are alerts.

### 6. Scheduled mode (cron)
The schedule is created only after the user's explicit yes to the interval (never more often than hourly; default every 4 hours). The cron prompt is:
"Run the screen-run skill in scheduled mode: run python3 files/scripts/screener.py run. If alerts is empty, send nothing. Otherwise send one message: each alert as 3–5 lines (what, what else lit up, why interesting, caveat), then one line that the full table is in the report file, and save the report."
Never create a second schedule; changing the interval replaces the existing task.

## Rules
- Every number in an explanation comes from this run's output. Never add news reasons you did not check; if the user wants the reason, offer coin-check with a news search.
- Never "buy" or "sell". An alert is unusual activity, not a signal to trade.
- Social is a proxy (trending + news), never call it "Twitter mentions".
