# Free data sources (checked 2026-10-12)

| Flag | Source | Notes |
|---|---|---|
| Universe | CoinGecko /coins/markets; CoinPaprika fallback | keyless CoinGecko rate-limits quickly; a free Demo key (COINGECKO_API_KEY) helps |
| Volume | Binance spot 24 h tickers + daily klines; Bybit, OKX for coins not on Binance | one exchange's spot volume, not the whole market |
| Futures | Binance futures (premium index, OI history, long/short); Bybit; Hyperliquid | Binance and Bybit block US servers; the script falls back automatically |
| Exchange flows | DefiLlama /protocol/<exchange> token balances | daily, delayed by hours; wallet reshuffles can look like flows |
| Social proxy | CoinGecko trending; GDELT news timeline | not X/Twitter; GDELT allows 1 request per 5 s |
| Large transfers | Blockscout (Ethereum) token transfers with wallet tags | Ethereum tokens only; busy tokens covered for part of the day |

Paid and therefore not used: CoinGlass, TradingView data, X API / Twitter Scout, LunarCrush, Whale Alert, Arkham, Dune API, Nansen.
