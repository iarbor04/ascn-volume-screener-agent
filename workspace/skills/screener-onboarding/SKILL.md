---
name: screener-onboarding
description: First conversation with a new user of the volume screener. Explains in plain words what the screener watches and when it writes, asks at most three questions (how often to check, how strict, optional free data key), runs the first screen and offers a schedule that starts only after an explicit yes. Use when the profile is empty, the user says hi, asks what the agent does or wants to set it up. Do not use when the user already asks about a coin (coin-check) or wants results now (screen-run).
---

> Before following this skill, run `python3 files/scripts/package.py skill screener-onboarding`: it records that the skill is in use, for the owner's reports.

# Onboarding

Output: `files/screener/profile/screener-profile.md` filled in. In chat: intro, up to three questions, the first screen.

## Steps

### 1. Check
`python3 files/scripts/screener.py context`. If the profile is filled, say what is set (schedule, strictness) and ask what to do.

### 2. Intro in plain words
First line: what the user gains: they hear about a coin where something unusual is happening while it is happening, not after. Then: you check the top coins (large ones, no stablecoins), compare today's trading with the usual, look at futures, money moving to and from exchanges, news and trending, large wallet transfers, and write only when several of these light up at once, with a short explanation. One line: alerts are about unusual activity, not buy or sell advice.

### 3. Questions (numbered, all skippable; always in the same reply as the intro, never a separate message)
1. How often to check: every hour, every 4 hours (recommended), twice a day? Each check spends a little of your credits.
2. How strict: write only when 3 of 5 signs match (recommended), stricter (4 of 5) or more alerts (2 of 5)?
3. Optional: a free CoinGecko key makes the coin list more reliable. If you have one, add it in Settings → Secrets as COINGECKO_API_KEY (never paste it in the chat).

### 4. Save and set
Write answers to the profile. Strictness → `screener.py config set min_flags <n>`. Show a 2-line summary, ask «Всё верно?».

### 5. First screen now
Run the screen-run skill once (manual mode) so the user sees what an alert looks like or that the market is quiet, with the 5 coins closest to an alert.

### 6. Schedule only with a yes
Offer the agreed interval; only after an explicit yes create the cron task described in screen-run, step 6. Never create it silently.

## Rules
- No jargon in onboarding: say "futures bets", "money moving to exchanges", "news", not OI, funding, netflow.
- Never ask for exchange keys, wallets or money; nothing is needed.
