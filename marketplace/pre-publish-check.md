# Pre-publish check

1. `python3 files/scripts/package.py check` → `clean: true`.
2. `files/screener/` has no test data (runs, alerts, profile), or run `python3 files/scripts/package.py prepublish`.
3. No cron job for the screen or the digest in the publishing workspace (`cron list`).
4. Soul field from `marketplace/soul-intro.md` (name Kai).
5. Start prompt from `marketplace/startup-task.md`; exclude paths from `marketplace/publish-exclude.txt`.
6. Secrets: none required; COINGECKO_API_KEY optional (free Demo key).
7. `python3 files/scripts/screener.py sources` from the publishing workspace: note which sources the ASCN server can reach (Binance and Bybit block US servers; fallbacks are automatic).
