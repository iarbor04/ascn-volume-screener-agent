# ascn-volume-screener-agent — Kai, crypto anomaly screener

ASCN (ascn.ai) marketplace agent built from the owner's spec "Агент №1: скринер аномальных объёмов". Scheduled screen of the top coins; five flags from free sources; alert when several fire; the LLM explains each alert.

| Skill | What it does |
|---|---|
| `screener-onboarding` | Plain intro, 3 questions (frequency, strictness, optional key), first run, schedule on yes |
| `screen-run` | Full screen, explanation per alert, scheduled mode silent when quiet |
| `coin-check` | One coin, all flags, optional news reason |
| `scoring-setup` | Thresholds and weights in plain words |
| `alerts-digest` | Alert history and price follow-up |

Script `workspace/files/scripts/screener.py`: `context`, `run`, `coin`, `config`, `alerts`, `followup`, `sources`, `report-path`. Standard library only. Sources: CoinGecko/CoinPaprika, Binance/Bybit/OKX spot and futures, Hyperliquid, DefiLlama exchange reserves, GDELT, Blockscout. Optional secret COINGECKO_API_KEY.

Install: `marketplace/install-or-update-from-github.md`; start prompt `marketplace/startup-task.md`; soul `marketplace/soul-intro.md`. After changes: `python3 tools/build_manifest.py && python3 tools/build_manifest.py --check`.
