# Reading signal combinations

Use these lines to explain an alert. Always with the numbers from the run; never as a forecast.

## Volume and price
- Volume ≥ 3× usual, price almost flat (|24 h| < 2%): heavy two-way trading; someone accumulates or distributes, or volume is washed. Worth watching.
- Volume ≥ 3×, price moves strongly (> 8%): a breakout or a dump with participation; check news.
- Taker-buy share > 0.6 / < 0.4: aggressive buyers / sellers dominate today's spot trading.

## Open interest (futures positions) vs price (`regime`)
- Price up, OI up: new longs; the move is backed by fresh bets.
- Price down, OI up: new shorts.
- Price up, OI down: shorts closing (squeeze); the move may fade once it is over.
- Price down, OI down: longs closing (liquidations or exits).
- Funding far from zero: one side pays a lot to hold; crowded trade.
- Long/short ≥ 2.5 or ≤ 0.6: accounts heavily on one side.

## Exchange flows (DefiLlama exchange reserves, ~24 h, daily data with a delay of hours)
- Inflow to exchanges: coins moved where they can be sold; often seen before selling.
- Outflow: coins moved off exchanges, often to hold or stake; less supply on the order books.
- Big unusual flows on a low-volume day can be exchange wallet reshuffles; mention it when the volume flag did not fire.

## Social proxy
- Trending on CoinGecko: many people are searching for the coin right now.
- News ratio ≥ 3: three times more news articles than the daily average of the past week (GDELT, news sites only).

## Large transfers (Ethereum tokens)
- Several transfers ≥ 1M USD in 24 h; to exchanges = possible selling, from exchanges = withdrawal.
- For busy tokens the free source covers only a part of the day: say "in the last N hours".

## Always add
- Which flags had no data.
- "Anomaly, not a direction call."
