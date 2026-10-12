# Скринер аномальных объёмов: бесплатные источники данных (исследование, 12.10.2026)

Все запросы ниже проверены живыми GET/POST-запросами 12.10.2026 (из не-US IP). «Ключ» = бесплатная регистрация. Лимиты взяты из документации и страниц цен.

## 0. Главное

- Связка **CoinGecko + Binance/Bybit/OKX + Hyperliquid + DefiLlama** закрывает объём, OI, funding, long/short и потоки на биржи **полностью бесплатно и почти без ключей**.
- **CoinGlass — платный** (от $29/мес, бесплатного API нет). **TradingView** публичного API не имеет. **Twitter Scout / X API, LunarCrush ($90/мес), Whale Alert ($29.95+/мес, только 7-дневный триал), Arkham (по заявке), Dune API (только триал/платно), DefiLlama unlocks (HTTP 402)** — бесплатно не получить.
- Слабое место — **соцсигнал**. Бесплатного аналога «рост упоминаний в X» в реальном времени нет. Есть только приближения.
- Фильтр «капитализация < $100M» внутри топ-100 сейчас **не отсеивает ни одной монеты**: у всех 100 капа ≥ $100M (проверено). Реально нужно другое: выкинуть стейблкоины, RWA и wrapped-токены (USDT, USDC, USDS, BUIDL, USYC, XAUT, PAXG, WBT и т.п.). После этого остаётся примерно 70–80 монет.

## 1. Источники по каждой потребности

### 1.1 Топ-100: капитализация, цена, объём 24ч

| Источник | Эндпоинт | Авторизация | Лимиты | Проверено |
|---|---|---|---|---|
| **CoinGecko** | `GET https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page=1` | без ключа или бесплатный Demo-ключ (заголовок `x-cg-demo-api-key`) | Без ключа лимит нестабильный: после ~10 запросов подряд шли сплошные 429. Demo: 100 запросов/мин, 10 000/мес | 200. Поля `market_cap`, `current_price`, `total_volume`, `market_cap_rank`, `price_change_percentage_24h` |
| **CoinPaprika** | `GET https://api.coinpaprika.com/v1/tickers?limit=100` | без ключа | заголовок `ratelimit-limit: 20000` (в месяц) | 200. `quotes.USD.price`, `volume_24h`, `volume_24h_change_24h`, `market_cap` |
| CoinMarketCap Basic | `pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest` | бесплатный ключ (`X-CMC_PRO_API_KEY`) | 15 000 кредитов/мес, 30 запросов/мин | без ключа: 401 «API key missing» |
| CoinCap | `rest.coincap.io/v3/assets` | теперь только с ключом | — | 401. Старый v2 мёртв |

**Лучший вариант без ключа — CoinPaprika** (стабильно, отдаёт ещё и `volume_24h_change_24h`). **Лучший в целом — CoinGecko с бесплатным Demo-ключом**: у него есть `id` для остальных эндпоинтов, trending и тикеры по биржам.

### 1.2 История объёма (замена TradingView): среднее за 20/30 дней и z-score

- **Binance spot klines** (без ключа): `GET https://api.binance.com/api/v3/klines?symbol=SOLUSDT&interval=1d&limit=31`. Поле [7] — quote volume в USDT, поле [10] — taker buy quote volume (бонус: доля агрессивных покупок). Лимит 6000 weight/мин, один запрос стоит 2 weight.
- **Bybit spot/linear kline** (без ключа): `GET https://api.bybit.com/v5/market/kline?category=spot&symbol=BTCUSDT&interval=D&limit=31`. Поле [6] — turnover в USDT.
- **OKX**: `GET https://www.okx.com/api/v5/market/candles?instId=BTC-USDT&bar=1D&limit=31`.
- **CoinGecko** `GET /api/v3/coins/{id}/market_chart?vs_currency=usd&days=30&interval=daily` отдаёт `total_volumes`, агрегированные по всем биржам. Проверено: 200. С Demo-ключом: 1 запрос на монету.
- **CoinPaprika** `GET /v1/tickers/{id}/historical?start=YYYY-MM-DD&interval=1d` (без ключа). Проверено: `volume_24h` и `market_cap` по дням.

Рекомендация: **основной источник — агрегированный объём CoinGecko**, он покрывает все монеты, включая те, которых нет на Binance. **Binance klines использовать для taker buy ratio** и для сравнения спота с перпами.

### 1.3 Деривативы: OI, funding, long/short, taker, ликвидации

**CoinGlass**: на странице цен только Hobbyist $29, Startup $79, Standard $299 и Professional $699. Бесплатного плана нет. Без ключа: `{"code":"401","msg":"API key missing."}`. **Не подходит.**

Бесплатные замены (все без ключа, все проверены и вернули 200):

| Метрика | Binance USDⓈ-M | Bybit v5 | OKX | Hyperliquid |
|---|---|---|---|---|
| OI сейчас | `fapi/v1/openInterest?symbol=` | `v5/market/tickers?category=linear` (**один запрос на все символы**: `openInterestValue`, `fundingRate`, `turnover24h`) | `api/v5/public/open-interest?instType=SWAP` | `POST /info {"type":"metaAndAssetCtxs"}` (**один запрос на все**: `openInterest`, `funding`, `dayNtlVlm`, `premium`) |
| История OI | `futures/data/openInterestHist?period=1d` (**максимум 30 дней**: на limit=40 пришло 30 строк) | `v5/market/open-interest?intervalTime=1d` | `rubik/stat/contracts/open-interest-volume?ccy=BTC&period=1D` (OI и объём по монете, суммарно по OKX) | — |
| Funding | `fapi/v1/premiumIndex` (без symbol вернёт все символы) и `fapi/v1/fundingRate` | `v5/market/funding/history` | `public/funding-rate` | в `metaAndAssetCtxs` |
| Long/short | `futures/data/globalLongShortAccountRatio` | `v5/market/account-ratio` (`buyRatio`/`sellRatio`) | `rubik/stat/contracts/long-short-account-ratio` | — |
| Taker buy/sell | `futures/data/takerlongshortRatio` (`buySellRatio`) | — | `rubik/stat/taker-volume` | — |
| Ликвидации | `fapi/v1/allForceOrders` **закрыт** (вернул HTML-страницу ошибки) | только websocket `allLiquidation` | **`public/liquidation-orders?instType=SWAP&uly=BTC-USDT&state=filled`** работает | — |

Лимиты: Binance fapi — 2400 weight/мин, эндпоинты `/futures/data/*` — около 1000 запросов за 5 минут на IP. Bybit — около 600 запросов за 5 секунд на IP. OKX rubik — 5 запросов за 2 секунды.

**Гео-блоки (критично для облака):** Binance (spot и fapi) отвечает **451** с IP из США. Bybit по собственной документации отдаёт **403** IP из США и материковой части Китая (блок на уровне CDN). OKX ограничивает пользователей из США. **Hyperliquid не блокирует.** Поэтому сервер должен быть в ЕС или Азии (Франкфурт, Сингапур). Из US-региона работают только Hyperliquid, CoinGecko и DefiLlama. Обходить блок через прокси нельзя: это нарушает ToS бирж. В коде нужен fallback по цепочке Binance → Bybit → OKX → Hyperliquid.

### 1.4 Соцупоминания (замена Twitter Scout)

Честно: **бесплатного real-time «упоминаний в X» в 2026 году нет.**

| Источник | Статус (проверено) | Пригодность |
|---|---|---|
| X API / Twitter Scout | платно | ✗ |
| LunarCrush | 401 без токена. API только с плана Light $90/мес | ✗ |
| **Santiment** `POST https://api.santiment.net/graphql`, метрика `social_volume_total` | **работает без ключа**, но последняя точка была от **12.09.2026, то есть лаг 30 дней**. Бесплатный ключ: 1000 запросов/мес, лаг тот же | только бэктест и калибровка ✗ |
| CryptoPanic | `/api/v1` за Cloudflare. Новый путь `/api/{growth\|enterprise}/v2` — платные планы | ✗ (бесплатного плана не нашли) |
| Reddit JSON | без OAuth **403 Blocked** | только через OAuth-приложение (бесплатно, около 100 запросов/мин; с конца 2025 новым приложениям, по сообщениям, нужно одобрение Reddit) |
| Neynar (Farcaster) | без ключа: x402 «payment or API key required» | бесплатный ключ возможен, но аудитория мала |
| **GDELT** `api.gdeltproject.org/api/v2/doc/doc?query=...&mode=timelinevolraw&format=json` | без ключа, **не чаще 1 запроса в 5 секунд** | ✓ рост числа новостей по монете (только новостные СМИ, не соцсети) |
| **CoinGecko trending** `/api/v3/search/trending` | 200, без ключа | ✓ попадание монеты в топ-15 поиска (сильный прокси хайпа) |
| CoinGecko `/coins/{id}` | `community_data` = **null** (Twitter и Telegram удалены). Остались `watchlist_portfolio_users` и `sentiment_votes_up_percentage` | ✓ Δ `watchlist_portfolio_users` за сутки (нужно хранить снимки) |
| Google Trends | официального API нет, неофициальные клиенты ловят 429 | ✗ |

**Рекомендованный бесплатный «соцфлаг»** складывается из трёх частей: (а) монета в CoinGecko trending, (б) рост `watchlist_portfolio_users` за 24 часа выше нормы, (в) объём новостей GDELT за 24 часа в 3 раза выше среднего за 7 дней. Владельцу нужно прямо сказать, что это **прокси, а не упоминания в X**.

### 1.5 Ончейн: крупные переводы и потоки на биржи

| Источник | Статус |
|---|---|
| **DefiLlama CEX** `GET https://api.llama.fi/protocol/binance-cex` (а также `okx`, `bybit`, `bitfinex` и др., всего 80 CEX в `/protocols`) | **без ключа, работает.** Поле `tokens` — ежедневные балансы бирж **в штуках по каждому токену** (1430 точек, 32 сети: BTC, ETH, SOL, TRON, BNB…). **Чистый поток токена = Δ баланса** по сумме крупных бирж. Это лучшая бесплатная замена «exchange netflow» |
| Etherscan API V2 | бесплатный ключ: 3–5 запросов/с, 100 000/день. **С конца 2025 бесплатный тариф не покрывает BNB, Base, OP и Avalanche.** Ethereum и Arbitrum бесплатны. `module=account&action=tokentx&address=<hot wallet>` (без ключа: «Missing/Invalid API Key») |
| Blockscout / Routescan | бесплатные эндпоинты в стиле Etherscan для Base, OP и других сетей |
| mempool.space | без ключа (BTC), работает. Крупные транзакции видно только перебором блоков: тяжело, но реально |
| Blockchair | без ключа быстро ловит бан (430 «IP temporary blacklisted») |
| Whale Alert | только триал, потом $29.95+/мес ✗ |
| Arkham | бесплатно только по заявке (pilot) ✗ для автоматизации |
| Dune API | по официальной документации API доступно только в триале или на платном плане ✗ |
| Covalent/GoldRush, Solscan Pro | бесплатные тарифы урезаны или требуют ключа. Не проверялось вживую — не закладывать |

**Реалистичный бесплатный подход:**
1. **Потоки на биржи** берём из DefiLlama CEX-балансов (около 10 крупнейших бирж): 10 запросов на прогон, все токены сразу, гранулярность **сутки**. Метки кошельков уже размечены командой DefiLlama.
2. **Крупные переводы** — только для ERC-20 на Ethereum и Arbitrum: Etherscan `tokentx` по статическому списку из 20–40 горячих кошельков бирж (метки Etherscan, захардкодить в конфиг), порог от $1M. Для BTC — опционально mempool.space, последние 6 блоков.
3. Ограничения: нативные L1 вне EVM (SOL, XRP, ADA, TON) без платных индексеров покрываются только суточными балансами DefiLlama. Списки кошельков устаревают, их нужно проверять раз в квартал.

## 2. «Какие ещё метрики?» — приоритет

| # | Сигнал | Бесплатный источник | Как флагать |
|---|---|---|---|
| 1 | Связка «цена + объём» | CoinGecko/Binance | объём ×3, а цена \|Δ\| < 2% — накопление/распределение или wash. Объём ×3 при \|Δ\| > 8% — пробой |
| 2 | ΔOI против Δцены (4 режима) | Binance/Bybit OI hist | OI↑ цена↑ = новые лонги. OI↑ цена↓ = новые шорты. OI↓ цена↑ = шорт-сквиз. OI↓ цена↓ = выход лонгов. Флаг: \|ΔOI24h\| ≥ 15% |
| 3 | Экстремальный funding | premiumIndex, HL | \|funding\| ≥ 0.05% за 8 часов или выше 95-го перцентиля за 30 дней |
| 4 | Перекос long/short | globalLongShortAccountRatio, Bybit account-ratio | L/S ≥ 2.5 или ≤ 0.6, либо z ≥ 2 |
| 5 | Taker buy ratio | klines поле [10], takerlongshortRatio | taker buy > 60% или < 40% объёма |
| 6 | Доля перп/спот | Binance spot + fapi 24hr | перп/спот ≥ 5 и рост вдвое (спекулятивный разгон) |
| 7 | Всплеск ликвидаций | OKX liquidation-orders | сумма за 24 часа ≥ 3× среднего |
| 8 | Концентрация объёма на одной бирже | CoinGecko `/coins/{id}/tickers` | ≥ 50% объёма на одной бирже или на бирже с `trust_score` не «green» — **понижать** вес (возможен wash) |
| 9 | Листинги/делистинги | Binance CMS `bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=48` (неофициальный, без ключа, работает; 161 — делистинги) | упоминание тикера в заголовке за 48 часов |
| 10 | CoinGecko trending rank | `/search/trending` | монета в топ-15 |
| 11 | DEX-объём и ликвидность | DexScreener `latest/dex/tokens/{addr}` (300 запросов/мин), GeckoTerminal (около 30 запросов/мин) | объём DEX за 24 часа ≥ 3× или ликвидность −30% |
| 12 | Приток стейблкоинов | `stablecoins.llama.fi/stablecoincharts/all` | рост капы стейблов за 7 дней > 2%. Это контекст рынка, не флаг монеты |
| 13 | Доминация BTC | CoinGecko `/global` | контекст для LLM (альтсезон или risk-off) |
| — | Токен-анлоки | DefiLlama `/emissions` = **HTTP 402**, бесплатного API нет | пропустить или вести ручной календарь в конфиге |

## 3. Рекомендуемый бесплатный стек

| Метрика | Источник | Эндпоинт | Ключ |
|---|---|---|---|
| Вселенная и капа | CoinGecko (fallback CoinPaprika) | `/coins/markets` | Demo (бесплатный), env `COINGECKO_API_KEY` |
| История объёма | CoinGecko | `/coins/{id}/market_chart?days=30&interval=daily` | Demo |
| Taker и спот | Binance spot | `/api/v3/klines` | нет |
| OI, funding, L/S | Binance fapi → Bybit → OKX → Hyperliquid | см. 1.3 | нет |
| Ликвидации | OKX | `public/liquidation-orders` | нет |
| Соцпрокси | CoinGecko trending + watchlist, GDELT | см. 1.4 | нет |
| Потоки на биржи | DefiLlama | `/protocol/{cex-slug}` | нет |
| Крупные переводы ERC-20 | Etherscan V2 (chainid 1, 42161) | `tokentx` | бесплатный, env `ETHERSCAN_API_KEY` |
| Листинги | Binance CMS | см. #9 | нет |

**Флаги и пороги по умолчанию** (все вынести в `config.json`):

- **F1 volume_spike**: `vol24h / mean30d ≥ 3` **и** `z = (vol24h − mean30d)/std30d ≥ 3`. Мягкий уровень: ×2 и z ≥ 2.
- **F2 social**: trending ИЛИ `Δwatchlist24h ≥ 2× медианы` ИЛИ `GDELT24h ≥ 3× mean7d` (любые 2 из 3, либо trending сам по себе).
- **F3 onchain_large**: ≥ 1 перевода ≥ $1M (или ≥ 0.1% капы) на или с хот-кошелька биржи за 24 часа.
- **F4 exchange_flow**: \|Δбаланса токена на CEX за 24 часа\| ≥ 1% от суммарного биржевого баланса или z ≥ 2.5 против 30-дневной истории. Знак: приток — медвежий, отток — бычий.
- **F5 derivs** (доп.): \|ΔOI24h\| ≥ 15% ИЛИ \|funding\| ≥ 0.05% ИЛИ L/S z ≥ 2.

**Скоринг:** веса по умолчанию: volume 0.35, derivs 0.20, exchange_flow 0.20, social 0.15, onchain_large 0.10. Алерт, если `score ≥ 0.6` **и** сработало `≥ 3` флагов (как у владельца). **Объём обязателен** (иначе это не «скринер объёмов»). Если данных по флагу нет (нет перпов, не EVM), его вес перераспределяется между остальными, а в алерте пишется «данных нет». LLM получает JSON с числами и режимом OI и пишет 3–5 строк объяснения.

**Бюджет запросов на прогон (около 80 монет):**

| Источник | Запросов | Лимит | Время |
|---|---|---|---|
| CoinGecko | 1 markets + 80 market_chart + 1 trending + 1 global (+80 coins/{id} для watchlist раз в сутки) | 100/мин | около 1–2 минут |
| Binance spot и fapi | 80 klines + 80×4 (OI hist, funding, L/S, taker) + 1 premiumIndex = около 400 | 2400 weight/мин; /futures/data около 1000 за 5 мин | около 1 минуты при паузе 150 мс |
| Bybit/HL bulk | 2 | — | секунды |
| OKX ликвидации | около 40 (только монеты с перпами) | 5 за 2 с (оценка) | около 20 секунд |
| DefiLlama CEX | около 10 | без явного лимита | около 30 секунд (ответы по 1–5 МБ) |
| Etherscan | около 30 кошельков | 3/с | около 15 секунд |
| GDELT | 80 | 1 в 5 секунд | **около 7 минут** — запускать раз в сутки или только для кандидатов с F1 |

Итого **около 700 запросов и 4–10 минут** на прогон. Месячный бюджет CoinGecko Demo (10 000) позволяет **около 4 полных прогонов в сутки** (около 85 запросов на прогон × 4 × 30 ≈ 10 200 — на грани). Отсюда правило: историю объёма кешировать и докачивать только последний день, тогда хватает и на ежечасный прогон.

## 4. Риски

1. **Гео-блоки:** Binance 451 и Bybit 403 с US-IP. Хостить в ЕС или Азии, держать fallback на OKX и Hyperliquid. Прокси для обхода не использовать.
2. **Лимиты:** CoinGecko без ключа почти сразу отдаёт 429 (проверено) — нужен Demo-ключ, кеш и экспоненциальный backoff. GDELT: 1 запрос в 5 секунд. Blockchair банит IP.
3. **Пробелы данных:** часть монет без перпов на Binance (а также стейблы, RWA, мелкие L1) — флаг derivs = «нет данных». История OI на Binance хранится только 30 дней. Потоки DefiLlama суточные и с задержкой в часы. Ончейн-переводы покрываются только EVM. Соцфлаг — прокси, а не X.
4. **Wash trading:** объём на одной бирже или на бирже с низким trust_score — понижать вес. Сверять агрегированный объём CoinGecko с суммой Binance+Bybit+OKX.
5. **Неофициальные эндпоинты** (Binance CMS) могут сломаться без предупреждения — оборачивать в try/except, не валить прогон.
6. **Ключи:** только через переменные окружения (`COINGECKO_API_KEY`, `ETHERSCAN_API_KEY`, опционально `REDDIT_CLIENT_ID/SECRET`, `CMC_API_KEY`). Не логировать, не класть в отчёт и в промпт LLM.
7. **Изменения тарифов:** Etherscan урезал бесплатные сети в 2025 году, CoinCap закрыл бесплатный v2, CryptoPanic убрал бесплатный план. Нужен еженедельный health-check каждого источника с алертом владельцу.
8. **Не инвестсовет:** алерт — это аномалия, а не сигнал к сделке. Так и писать в тексте LLM.
