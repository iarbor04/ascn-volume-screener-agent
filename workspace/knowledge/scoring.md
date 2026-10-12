# Scoring and settings (defaults)

Score = sum of weights of fired flags / sum of weights of flags with data. A coin alerts when: fired flags ≥ min_flags, score ≥ min_score, and the volume flag fired (require_volume). Flags without data are left out of both sums.

| Key | Default | Meaning |
|---|---|---|
| top_n | 100 | coins by market cap |
| min_market_cap | 100000000 | minimum market cap, USD |
| exclude_symbols | stablecoins, wrapped, tokenized assets | skipped tickers |
| weights.volume / derivs / flow / social / onchain | 0.35 / 0.20 / 0.20 / 0.15 / 0.10 | importance; 0 turns a flag off |
| min_flags | 3 | how many flags must fire |
| min_score | 0.6 | minimum weighted score |
| require_volume | true | volume flag must be among them |
| cooldown_hours | 12 | no repeat alert for a coin unless its score grows |
| volume_ratio, volume_z | 3, 3 | 24 h volume vs 30-day average: multiple and z-score, both needed |
| oi_change_pct | 15 | open interest change in 24 h, % |
| funding_abs_pct | 0.05 | funding per period, % |
| long_short_high / low | 2.5 / 0.6 | account long/short ratio extremes |
| flow_pct, flow_z | 2, 2.5 | net exchange flow, % of reserves, and unusualness; both needed |
| news_ratio | 3 | news today vs daily average of the past week |
| trending_counts | true | CoinGecko trending fires the social flag |
| onchain_usd, onchain_min_count | 1000000, 2 | large transfer size and how many are needed |
| cex_slugs | 8 largest exchanges | DefiLlama exchanges summed for flows |

Owner's original idea: "3 of 4 flags"; here 3 of 5 (futures added as its own flag), volume required.
