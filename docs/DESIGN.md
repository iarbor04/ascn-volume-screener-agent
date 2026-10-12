# Design decisions

Owner spec (2026-10-12): scheduled; CMC top-100, drop caps < 100M; sources CoinGlass (volume, OI), TradingView (volume vs daily average), Twitter Scout (mentions), on-chain transfers and exchange in/outflow; one flag per source; alert when e.g. 3 of 4 fire; thresholds and weights configurable; the LLM gets the numbers as a table and writes a short explanation. Owner constraint: **all APIs free**.

Replacements (research in docs/research.md, all checked live 2026-10-12):
- CMC top-100 → CoinGecko /coins/markets (keyless; free Demo key optional), CoinPaprika fallback. CMC needs a key even on the free plan; CoinGecko gives the same list. The 100M cap filter drops nothing today, so stablecoins, wrapped and tokenized assets are excluded as well (configurable list).
- CoinGlass (paid from $29) → Binance futures, Bybit, Hyperliquid public endpoints (OI history, funding, long/short). OI became its own flag ("derivs"), so the scheme is 3 of 5 with volume required.
- TradingView (no public API) → exchange spot 24 h volume vs 30 daily candles: ratio and z-score.
- Twitter Scout / X API (paid) → CoinGecko trending + GDELT news volume. Labeled a proxy everywhere.
- On-chain → DefiLlama exchange reserves (net flow ~24 h, all tokens, 8 exchanges) for in/outflow; Blockscout Ethereum token transfers with wallet tags for large transfers (keyless; Etherscan needs a key and dropped free chains). Native coins and non-Ethereum tokens have no transfer data → the flag is "no data" and its weight is redistributed.
- Slow checks (GDELT 1 request per 5 s, Blockscout paging) run only for candidates (volume flag or 2 other flags) to keep a run within ~3–5 minutes.
- Cooldown 12 h per coin unless the score grows; quiet scheduled runs send nothing (saves credits).
- Flow flag needs both a % move and an unusual z-score: with "either", 26 of 79 coins fired on the first live run (DefiLlama wallet reshuffles).
- Live runs 2026-10-12: first 79 coins, 181 s, 1 alert (PYTH: volume 3.5×, OI +20%, outflow −2.6% z −3.7, trending #10); after the fixes 75 coins, 154 s, flow fired on 5 coins instead of 26, volume missing for 5 coins instead of 21, same single alert. GDELT answered 429 from the build machine after many test calls: the flag works without it.
- Name Kai is a placeholder.
