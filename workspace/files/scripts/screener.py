#!/usr/bin/env python3
"""Anomalous volume screener: free public data only, standard library only, prints JSON.

Universe: CoinGecko top-N by market cap (CoinPaprika if CoinGecko fails), market cap >= min, without stablecoins,
wrapped and tokenized assets. Five flags per coin, each from its own free source:
  volume   24 h volume vs the 30-day daily average and z-score (Binance spot; Bybit, OKX as fallbacks)
  derivs   open interest change over 24 h, funding extreme, long/short extreme (Binance futures; Bybit; Hyperliquid)
  flow     net exchange inflow/outflow of the token over ~24 h (DefiLlama exchange reserves, top exchanges)
  social   CoinGecko trending, news volume vs the week before (GDELT); a proxy, not X/Twitter mentions
  onchain  large ERC-20 transfers in the last 24 h, with exchange-tagged wallets marked (Blockscout, Ethereum)
A coin alerts when the weighted score of fired flags >= min_score AND at least min_flags fired (volume required by
default). Flags without data are left out of the score and listed as "no data". Thresholds and weights live in
files/screener/config.json. Optional free keys from Settings -> Secrets: COINGECKO_API_KEY (Demo).

  context                         config, last run, alerts in the last 24 h, today's date
  run [--top N] [--no-slow] [--force]
                                  full screen; slow checks (news, on-chain) only for candidates; writes
                                  files/screener/runs/<time>.json; "alerts" holds coins that passed, new since the
                                  cooldown; "near" holds coins one flag short
  coin <SYMBOL>                   every metric and flag for one coin, slow checks included, no gating, no cooldown
  config show | config set <key> <value> | config reset
  alerts [--days N]               alert history
  followup [--days N]             price at each alert vs now: did the alerts catch real moves
  sources                         one test call per source: ok / blocked / error
  report-path <topic>             path for today's report file
"""
import argparse
import json
import math
import os
import re
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(os.environ.get("SCREENER_ROOT") or Path(__file__).resolve().parents[2])
DATA = ROOT / "files" / "screener"
CONFIG = DATA / "config.json"
RUNS = DATA / "runs"
CACHE = DATA / "cache"
ALERTS = DATA / "alerts.jsonl"
REPORTS = DATA / "reports"
UA = "Mozilla/5.0 (compatible; ascn-screener/1.0)"

DEFAULTS = {
    "top_n": 100, "min_market_cap": 100_000_000,
    "exclude_symbols": ["USDT", "USDC", "DAI", "USDS", "USDE", "FDUSD", "TUSD", "PYUSD", "USD1", "USDD", "RLUSD", "USDF",
                        "BUIDL", "USYC", "USTB", "OUSG", "XAUT", "PAXG", "WBTC", "WETH", "WBETH", "STETH", "WSTETH",
                        "WEETH", "CBBTC", "CBETH", "RETH", "METH", "LBTC", "SOLVBTC", "BTCB", "WBT", "BSC-USD", "SUSDE",
                        "SUSDS", "JITOSOL", "MSOL", "BNSOL", "EZETH", "RSETH", "USD0", "GHO", "FRAX", "LUSD", "CRVUSD",
                        "USDY", "USDG", "FIGR_HELOC", "EURSAFO", "BCAP", "EURC", "USDTB", "SYRUPUSDC"],
    "weights": {"volume": 0.35, "derivs": 0.20, "flow": 0.20, "social": 0.15, "onchain": 0.10},
    "min_flags": 3, "min_score": 0.6, "require_volume": True, "cooldown_hours": 12,
    "volume_ratio": 3.0, "volume_z": 3.0,
    "oi_change_pct": 15.0, "funding_abs_pct": 0.05, "long_short_high": 2.5, "long_short_low": 0.6,
    "flow_pct": 2.0, "flow_z": 2.5,
    "news_ratio": 3.0, "trending_counts": True,
    "onchain_usd": 1_000_000, "onchain_min_count": 2, "onchain_pages": 4,
    "cex_slugs": ["binance-cex", "okx", "bitfinex", "bybit", "gate", "bitget", "mexc", "htx"],
    "exchange_tags": ["binance", "coinbase", "okx", "okex", "kraken", "bybit", "bitfinex", "kucoin", "gate", "htx",
                      "huobi", "bitget", "mexc", "crypto.com", "upbit", "gemini", "bitstamp", "robinhood", "bithumb"],
}
FLAGS = ["volume", "derivs", "flow", "social", "onchain"]


def out(obj, code=0):
    print(json.dumps(obj, ensure_ascii=False, indent=1))
    sys.exit(code)


def now():
    return datetime.now(timezone.utc)


def read_json(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def cfg():
    c = json.loads(json.dumps(DEFAULTS))
    user = read_json(CONFIG, {})
    for k, v in user.items():
        if k == "weights" and isinstance(v, dict):
            c["weights"].update(v)
        else:
            c[k] = v
    return c


class Blocked(Exception):
    pass


STATS = {"requests": 0, "errors": {}}


def http(url, params=None, data=None, headers=None, tries=3, timeout=30):
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    h = {"User-Agent": UA, "Accept": "application/json"}
    h.update(headers or {})
    body = json.dumps(data).encode() if data is not None else None
    if body:
        h["Content-Type"] = "application/json"
    host = urllib.parse.urlparse(url).netloc
    last = None
    for i in range(tries):
        STATS["requests"] += 1
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=h), timeout=timeout) as r:
                raw = r.read().decode("utf-8")
            return json.loads(raw)
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code in (451, 403):
                STATS["errors"][host] = last
                raise Blocked(f"{host}: {last}")
            if e.code in (400, 404):
                break
            time.sleep((2 ** i) * (3 if e.code == 429 else 1))
        except (json.JSONDecodeError, UnicodeDecodeError):
            last = "not JSON"
            time.sleep(5)
        except Exception as e:  # network
            last = type(e).__name__
            time.sleep(1.5 * (i + 1))
    STATS["errors"][host] = last
    return None


def cached(name, hours, fn):
    p = CACHE / f"{name}.json"
    c = read_json(p, None)
    if c and time.time() - c.get("_at", 0) < hours * 3600:
        return c["data"]
    data = fn()
    if data is not None:
        write_json(p, {"_at": time.time(), "data": data})
    return data if data is not None else (c or {}).get("data")


def rnd(x, n=2):
    return None if x is None or (isinstance(x, float) and not math.isfinite(x)) else round(x, n)


# ---------- universe ----------

def universe(c):
    key = os.environ.get("COINGECKO_API_KEY")
    hdr = {"x-cg-demo-api-key": key} if key else None
    coins, source = [], None
    r = http("https://api.coingecko.com/api/v3/coins/markets",
             {"vs_currency": "usd", "order": "market_cap_desc", "per_page": min(c["top_n"], 250), "page": 1,
              "price_change_percentage": "24h"}, headers=hdr)
    if isinstance(r, list) and r:
        source = "coingecko"
        for x in r:
            coins.append({"id": x["id"], "symbol": x["symbol"].upper(), "name": x["name"], "rank": x.get("market_cap_rank"),
                          "market_cap": x.get("market_cap") or 0, "price": x.get("current_price"),
                          "volume_24h_all": x.get("total_volume"), "change_24h": x.get("price_change_percentage_24h")})
    else:
        r = http("https://api.coinpaprika.com/v1/tickers", {"limit": c["top_n"]}) or []
        source = "coinpaprika"
        for x in r:
            q = (x.get("quotes") or {}).get("USD") or {}
            coins.append({"id": x["id"], "symbol": x["symbol"].upper(), "name": x["name"], "rank": x.get("rank"),
                          "market_cap": q.get("market_cap") or 0, "price": q.get("price"),
                          "volume_24h_all": q.get("volume_24h"), "change_24h": q.get("percent_change_24h")})
    excl = set(s.upper() for s in c["exclude_symbols"])
    kept, dropped = [], []
    for x in coins[:c["top_n"]]:
        stable = (x["price"] and 0.97 <= x["price"] <= 1.03 and "USD" in x["symbol"])
        if x["symbol"] in excl or stable:
            dropped.append(x["symbol"] + " (stable/wrapped)")
        elif x["market_cap"] < c["min_market_cap"]:
            dropped.append(x["symbol"] + " (cap)")
        else:
            kept.append(x)
    return kept, dropped, source


# ---------- volume ----------

def spot_tickers():
    """24 h rolling quote volume and price change by base symbol, per venue: Binance, Bybit, OKX (each that answers)."""
    venues = []
    try:
        r = http("https://api.binance.com/api/v3/ticker/24hr", {"type": "FULL"})
        if isinstance(r, list) and r:
            venues.append(("binance", {x["symbol"][:-4]: {"vol": float(x["quoteVolume"]), "chg": float(x["priceChangePercent"])}
                                       for x in r if x["symbol"].endswith("USDT")}))
    except Blocked:
        pass
    try:
        r = http("https://api.bybit.com/v5/market/tickers", {"category": "spot"})
        lst = ((r or {}).get("result") or {}).get("list") or []
        if lst:
            venues.append(("bybit", {x["symbol"][:-4]: {"vol": float(x["turnover24h"]), "chg": float(x["price24hPcnt"]) * 100}
                                     for x in lst if x["symbol"].endswith("USDT")}))
    except Blocked:
        pass
    try:
        r = http("https://www.okx.com/api/v5/market/tickers", {"instType": "SPOT"}) or {}
        res = {}
        for x in r.get("data") or []:
            if x["instId"].endswith("-USDT"):
                o, l = float(x["open24h"] or 0), float(x["last"] or 0)
                res[x["instId"][:-5]] = {"vol": float(x["volCcy24h"] or 0), "chg": (l / o - 1) * 100 if o else None}
        if res:
            venues.append(("okx", res))
    except Blocked:
        pass
    return venues


def pick_spot(venues, sym):
    for v, d in venues:
        if sym in d and d[sym]["vol"] > 0:
            return v, d[sym]
    return None, None


def daily_volumes(venue, sym):
    """Quote volume for the last 30 complete days (oldest first) and today's taker-buy share where available."""
    try:
        if venue == "binance":
            k = http("https://api.binance.com/api/v3/klines", {"symbol": sym + "USDT", "interval": "1d", "limit": 31})
            if not k:
                return None, None
            vols = [float(x[7]) for x in k[:-1]]
            today = k[-1]
            taker = float(today[10]) / float(today[7]) if float(today[7]) else None
            return vols[-30:], taker
        if venue == "bybit":
            r = http("https://api.bybit.com/v5/market/kline", {"category": "spot", "symbol": sym + "USDT", "interval": "D",
                                                               "limit": 31})
            k = list(reversed(((r or {}).get("result") or {}).get("list") or []))
            return ([float(x[6]) for x in k[:-1]][-30:] if k else None), None
        r = http("https://www.okx.com/api/v5/market/candles", {"instId": sym + "-USDT", "bar": "1Dutc", "limit": 31})
        k = list(reversed((r or {}).get("data") or []))
        return ([float(x[7]) for x in k[:-1]][-30:] if k else None), None
    except Blocked:
        return None, None


def volume_flag(c, vol24, hist):
    if not vol24 or not hist or len(hist) < 14:
        return None, {"note": "not enough history"}
    mean = statistics.mean(hist)
    sd = statistics.pstdev(hist) or 1.0
    ratio, z = vol24 / mean if mean else None, (vol24 - mean) / sd
    fired = bool(ratio and ratio >= c["volume_ratio"] and z >= c["volume_z"])
    return fired, {"vol_24h": rnd(vol24, 0), "avg_30d": rnd(mean, 0), "ratio": rnd(ratio), "z": rnd(z), "days": len(hist)}


# ---------- derivatives ----------

def derivs_bulk():
    res = {"venue": None, "funding": {}, "oi_now": {}}
    try:
        r = http("https://fapi.binance.com/fapi/v1/premiumIndex")
        if isinstance(r, list) and r:
            res["venue"] = "binance"
            res["funding"] = {x["symbol"][:-4]: float(x["lastFundingRate"]) * 100 for x in r if x["symbol"].endswith("USDT")}
            return res
    except Blocked:
        pass
    try:
        r = http("https://api.bybit.com/v5/market/tickers", {"category": "linear"})
        lst = ((r or {}).get("result") or {}).get("list") or []
        if lst:
            res["venue"] = "bybit"
            for x in lst:
                if x["symbol"].endswith("USDT"):
                    s = x["symbol"][:-4]
                    res["funding"][s] = float(x["fundingRate"] or 0) * 100
                    res["oi_now"][s] = float(x["openInterestValue"] or 0)
            return res
    except Blocked:
        pass
    r = http("https://api.hyperliquid.xyz/info", data={"type": "metaAndAssetCtxs"})
    if isinstance(r, list) and len(r) == 2:
        res["venue"] = "hyperliquid"
        for u, ctx in zip(r[0]["universe"], r[1]):
            res["funding"][u["name"]] = float(ctx["funding"]) * 100
            res["oi_now"][u["name"]] = float(ctx["openInterest"]) * float(ctx["markPx"])
    return res


def derivs_coin(c, venue, sym, bulk, prev_oi):
    if sym not in bulk["funding"]:
        return None, {"note": "no perpetual contract found"}
    d = {"venue": venue, "funding_pct": rnd(bulk["funding"][sym], 4)}
    try:
        if venue == "binance":
            h = http("https://fapi.binance.com/futures/data/openInterestHist", {"symbol": sym + "USDT", "period": "1h", "limit": 25})
            if h and len(h) >= 2:
                a, b = float(h[0]["sumOpenInterestValue"]), float(h[-1]["sumOpenInterestValue"])
                d["oi_usd"], d["oi_change_24h_pct"] = rnd(b, 0), rnd((b / a - 1) * 100 if a else None)
            ls = http("https://fapi.binance.com/futures/data/globalLongShortAccountRatio",
                      {"symbol": sym + "USDT", "period": "1h", "limit": 1})
            if ls:
                d["long_short"] = rnd(float(ls[-1]["longShortRatio"]))
        elif venue == "bybit":
            r = http("https://api.bybit.com/v5/market/open-interest", {"category": "linear", "symbol": sym + "USDT",
                                                                       "intervalTime": "1h", "limit": 25})
            lst = ((r or {}).get("result") or {}).get("list") or []
            if len(lst) >= 2:
                a, b = float(lst[-1]["openInterest"]), float(lst[0]["openInterest"])
                d["oi_change_24h_pct"] = rnd((b / a - 1) * 100 if a else None)
            d["oi_usd"] = rnd(bulk["oi_now"].get(sym), 0)
            r = http("https://api.bybit.com/v5/market/account-ratio", {"category": "linear", "symbol": sym + "USDT",
                                                                       "period": "1h", "limit": 1})
            lst = ((r or {}).get("result") or {}).get("list") or []
            if lst and float(lst[0]["sellRatio"]):
                d["long_short"] = rnd(float(lst[0]["buyRatio"]) / float(lst[0]["sellRatio"]))
        else:
            now_oi = bulk["oi_now"].get(sym)
            d["oi_usd"] = rnd(now_oi, 0)
            p = (prev_oi or {}).get(sym)
            if p and now_oi and 18 <= (time.time() - p["t"]) / 3600 <= 30:
                d["oi_change_24h_pct"] = rnd((now_oi / p["v"] - 1) * 100)
    except Blocked:
        pass
    fired = []
    if d.get("oi_change_24h_pct") is not None and abs(d["oi_change_24h_pct"]) >= c["oi_change_pct"]:
        fired.append("open interest")
    if abs(d["funding_pct"] or 0) >= c["funding_abs_pct"]:
        fired.append("funding")
    ls = d.get("long_short")
    if ls and (ls >= c["long_short_high"] or ls <= c["long_short_low"]):
        fired.append("long/short")
    d["fired_by"] = fired
    return bool(fired), d


def oi_regime(price_chg, oi_chg):
    if price_chg is None or oi_chg is None:
        return None
    if oi_chg >= 0:
        return "new longs (price up, OI up)" if price_chg >= 0 else "new shorts (price down, OI up)"
    return "short squeeze / shorts closing (price up, OI down)" if price_chg >= 0 else "longs closing (price down, OI down)"


# ---------- exchange flow ----------

def cex_series(c):
    """{SYMBOL: [[ts, total balance across exchanges], ...]} daily-ish, last 35 days. Cached 6 h."""
    def load():
        agg, used = {}, []
        cutoff = time.time() - 36 * 86400
        with ThreadPoolExecutor(4) as ex:
            got = list(ex.map(lambda sl: (sl, http(f"https://api.llama.fi/protocol/{sl}", timeout=120)), c["cex_slugs"]))
        for slug, r in got:
            if not r or not r.get("tokens"):
                continue
            used.append(slug)
            for pt in r["tokens"]:
                if pt["date"] < cutoff:
                    continue
                day = int(pt["date"] // 3600 * 3600)
                for sym, amt in (pt.get("tokens") or {}).items():
                    s = sym.upper()
                    agg.setdefault(s, {}).setdefault(slug, []).append([day, amt])
        return {"exchanges": used, "tokens": agg}
    return cached("cex", 6, load) or {"exchanges": [], "tokens": {}}


def flow_coin(c, sym, cex):
    per = cex["tokens"].get(sym)
    if not per:
        return None, {"note": "token not found in exchange reserves"}
    # align: for each exchange take the last point and the point ~24 h before; daily deltas for the z-score
    now_tot = prev_tot = 0.0
    deltas = {}
    for slug, pts in per.items():
        pts = sorted(pts)
        last_t, last_v = pts[-1]
        before = [p for p in pts if p[0] <= last_t - 20 * 3600]
        if not before:
            continue
        now_tot += last_v
        prev_tot += before[-1][1]
        for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
            deltas[t1 // 86400] = deltas.get(t1 // 86400, 0) + (v1 - v0)
    if prev_tot <= 0:
        return None, {"note": "no 24 h history"}
    net = now_tot - prev_tot
    pct = net / prev_tot * 100
    hist = list(deltas.values())[:-1][-30:]
    z = (net - statistics.mean(hist)) / (statistics.pstdev(hist) or 1) if len(hist) >= 10 else None
    fired = abs(pct) >= c["flow_pct"] and (z is None or abs(z) >= c["flow_z"])
    return fired, {"exchanges": len(per), "balance_tokens": rnd(now_tot, 0), "net_24h_tokens": rnd(net, 0),
                   "net_24h_pct": rnd(pct), "z": rnd(z), "direction": "inflow to exchanges" if net > 0 else "outflow from exchanges"}


# ---------- social ----------

def trending():
    r = http("https://api.coingecko.com/api/v3/search/trending") or {}
    return {x["item"]["symbol"].upper(): i + 1 for i, x in enumerate(r.get("coins") or [])}


LAST_GDELT = [0.0]
GDELT_LOCK = threading.Lock()
GDELT_DOWN = [False]


def news_ratio(name, sym):
    """GDELT allows one request per 5 s and often refuses cloud servers: after one refusal it is skipped for the run."""
    with GDELT_LOCK:
        if GDELT_DOWN[0]:
            return None
        wait = 5.5 - (time.time() - LAST_GDELT[0])
        if wait > 0:
            time.sleep(wait)
        LAST_GDELT[0] = time.time()
        return _news(name, sym)


def _news(name, sym):
    q = f'"{name}" ({sym} OR crypto OR token)' if len(sym) <= 3 or sym.isalpha() and len(name) > 3 else f'"{name}"'
    r = http("https://api.gdeltproject.org/api/v2/doc/doc",
             {"query": q, "mode": "timelinevolraw", "format": "json", "timespan": "7d"}, tries=1)
    try:
        pts = r["timeline"][0]["data"]
    except Exception:
        GDELT_DOWN[0] = True
        return None
    vals = [p.get("value", 0) for p in pts]
    if len(vals) < 24:
        return None
    step = max(1, len(vals) // 7)  # points per day
    last = sum(vals[-step:])
    before = vals[:-step]
    base = (sum(before) / (len(before) / step)) if before else 0
    return {"articles_24h": last, "avg_per_day_before": rnd(base, 1), "ratio": rnd(last / base) if base else None}


def social_coin(c, x, trend, slow):
    d = {"trending_rank": trend.get(x["symbol"]), "news": None, "proxy": "CoinGecko trending + GDELT news; not X mentions"}
    if slow:
        d["news"] = news_ratio(x["name"], x["symbol"])
    fired = []
    if d["trending_rank"] and c["trending_counts"]:
        fired.append("trending")
    if d["news"] and d["news"]["ratio"] and d["news"]["ratio"] >= c["news_ratio"]:
        fired.append("news")
    d["fired_by"] = fired
    if not trend and d["news"] is None:
        return None, d  # both social sources unavailable
    return bool(fired), d


# ---------- on-chain ----------

def platforms():
    def load():
        r = http("https://api.coingecko.com/api/v3/coins/list", {"include_platform": "true"}, timeout=60) or []
        return {x["id"]: (x.get("platforms") or {}).get("ethereum") for x in r if (x.get("platforms") or {}).get("ethereum")}
    return cached("eth-contracts", 24 * 7, load) or {}


def onchain_coin(c, x, contracts):
    addr = contracts.get(x["id"])
    if not addr:
        return None, {"note": "no Ethereum token contract (native coin or other chain): not covered"}
    since = now() - timedelta(hours=24)
    big, covered_from, params = [], None, None
    tags = [t.lower() for t in c["exchange_tags"]]
    for _ in range(c["onchain_pages"]):
        r = http(f"https://eth.blockscout.com/api/v2/tokens/{addr}/transfers", params)
        items = (r or {}).get("items") or []
        if not items:
            break
        stop = False
        for it in items:
            ts = datetime.fromisoformat(it["timestamp"].replace("Z", "+00:00"))
            covered_from = ts
            if ts < since:
                stop = True
                break
            tot, tok = it.get("total") or {}, it.get("token") or {}
            try:
                amt = int(tot.get("value") or 0) / 10 ** int(tot.get("decimals") or tok.get("decimals") or 18)
                usd = amt * float(tok.get("exchange_rate") or x["price"] or 0)
            except (TypeError, ValueError):
                continue
            if usd >= c["onchain_usd"]:
                def label(side):
                    names = [((t.get("meta") or {}).get("projectName") or t.get("name") or "")
                             for t in (((it.get(side) or {}).get("metadata") or {}).get("tags") or [])]
                    names.append((it.get(side) or {}).get("name") or "")
                    hit = [n for n in names if any(k in n.lower() for k in tags)]
                    return hit[0] if hit else None
                big.append({"time": it["timestamp"][:16], "usd": rnd(usd, 0), "from_exchange": label("from"),
                            "to_exchange": label("to"), "tx": it.get("transaction_hash")})
        if stop:
            break
        params = r.get("next_page_params")
        if not params:
            break
    hours = rnd((now() - covered_from).total_seconds() / 3600, 1) if covered_from else None
    d = {"chain": "ethereum", "covered_hours": min(hours or 0, 24), "large_transfers": len(big),
         "large_usd": rnd(sum(b["usd"] for b in big), 0),
         "to_exchanges_usd": rnd(sum(b["usd"] for b in big if b["to_exchange"]), 0),
         "from_exchanges_usd": rnd(sum(b["usd"] for b in big if b["from_exchange"]), 0), "top": sorted(big, key=lambda b: -b["usd"])[:5]}
    if hours is not None and hours < 24:
        d["note"] = f"busy token: the free source covered only the last {d['covered_hours']} h"
    if len(big) < c["onchain_min_count"] and (hours or 0) < 6:
        return None, d  # too short a window to say "no large transfers"
    return len(big) >= c["onchain_min_count"], d


# ---------- scoring ----------

def score(c, flags):
    w = c["weights"]
    avail = [f for f in FLAGS if flags.get(f) is not None]
    fired = [f for f in avail if flags[f]]
    tot = sum(w.get(f, 0) for f in avail)
    s = sum(w.get(f, 0) for f in fired) / tot if tot else 0
    ok = len(fired) >= c["min_flags"] and s >= c["min_score"] and (flags.get("volume") or not c["require_volume"])
    return {"score": rnd(s), "fired": fired, "no_data": [f for f in FLAGS if flags.get(f) is None], "passes": ok,
            "flags_needed": c["min_flags"]}


def analyse(c, x, ctx, slow):
    sym = x["symbol"]
    flags, m = {}, {"symbol": sym, "name": x["name"], "rank": x["rank"], "market_cap": rnd(x["market_cap"], 0),
                    "price": x["price"], "price_change_24h_pct": rnd(x["change_24h"]),
                    "volume_24h_all_exchanges": rnd(x["volume_24h_all"], 0)}
    venue, t = pick_spot(ctx["spot"], sym)
    hist, taker = daily_volumes(venue, sym) if t else (None, None)
    flags["volume"], m["volume"] = volume_flag(c, t["vol"] if t else None, hist)
    m["volume"]["venue"] = venue
    if not t:
        m["volume"]["note"] = "no USDT spot pair on Binance, Bybit or OKX"
    if taker is not None:
        m["volume"]["taker_buy_share_today"] = rnd(taker)
    if t and t.get("chg") is not None:
        m["price_change_24h_pct"] = rnd(t["chg"])
    flags["derivs"], m["derivs"] = derivs_coin(c, ctx["derivs"]["venue"], sym, ctx["derivs"], ctx.get("prev_oi"))
    if isinstance(m["derivs"], dict):
        m["derivs"]["regime"] = oi_regime(m["price_change_24h_pct"], m["derivs"].get("oi_change_24h_pct"))
    flags["flow"], m["flow"] = flow_coin(c, sym, ctx["cex"])
    cheap = sum(1 for f in ("volume", "derivs", "flow") if flags[f])
    go_slow = slow and (flags["volume"] or cheap >= 2)
    flags["social"], m["social"] = social_coin(c, x, ctx["trending"], go_slow)
    if go_slow:
        flags["onchain"], m["onchain"] = onchain_coin(c, x, ctx["contracts"])
    else:
        flags["onchain"], m["onchain"] = None, {"note": "checked only for candidates (volume flag or 2 other flags)"}
    m["flags"] = {f: flags[f] for f in FLAGS}
    m["result"] = score(c, flags)
    return m


def context_data(c, need_slow):
    spot = spot_tickers()
    d = derivs_bulk()
    prev = read_json(CACHE / "hl-oi.json", {})
    if d["venue"] == "hyperliquid":
        write_json(CACHE / "hl-oi.json", {s: {"t": time.time(), "v": v} for s, v in d["oi_now"].items()}
                   if not prev or time.time() - list(prev.values())[0]["t"] > 20 * 3600 else prev)
    return {"spot": spot, "derivs": d, "prev_oi": prev, "cex": cex_series(c),
            "trending": trending() or {}, "contracts": platforms() if need_slow else {}}


# ---------- commands ----------

def cmd_context(a):
    c = cfg()
    runs = sorted(RUNS.glob("*.json"))
    last = read_json(runs[-1], {}) if runs else {}
    recent = [json.loads(l) for l in ALERTS.read_text().splitlines()] if ALERTS.exists() else []
    day_ago = (now() - timedelta(hours=24)).isoformat()
    pf = DATA / "profile" / "screener-profile.md"
    prof = pf.read_text(encoding="utf-8") if pf.exists() else ""
    filled = [l for l in prof.splitlines() if ":" in l and not l.startswith(("#", "Updated"))
              and l.split(":", 1)[1].strip() and not l.split(":", 1)[1].strip().startswith("(")]
    out({"ok": True, "today_utc": now().date().isoformat(), "profile_filled": bool(filled),
         "profile": prof.strip() if filled else "", "config": c,
         "keys": {"COINGECKO_API_KEY": bool(os.environ.get("COINGECKO_API_KEY"))},
         "last_run": {k: last.get(k) for k in ("at", "coins", "alerts_count", "sources", "duration_s")} if last else None,
         "alerts_24h": [r for r in recent if r["at"] >= day_ago]})


def cmd_run(a):
    c = cfg()
    if a.top:
        c["top_n"] = a.top
    t0 = time.time()
    coins, dropped, src = universe(c)
    if not coins:
        out({"ok": False, "error": "could not load the coin list", "errors": STATS["errors"]}, 1)
    ctx = context_data(c, not a.no_slow)
    with ThreadPoolExecutor(6) as ex:
        rows = list(ex.map(lambda x: analyse(c, x, ctx, not a.no_slow), coins))
    hist = [json.loads(l) for l in ALERTS.read_text().splitlines()] if ALERTS.exists() else []
    cutoff = (now() - timedelta(hours=c["cooldown_hours"])).isoformat()
    alerts, repeats = [], []
    for r in rows:
        if not r["result"]["passes"]:
            continue
        prev = [h for h in hist if h["symbol"] == r["symbol"] and h["at"] >= cutoff]
        if prev and not a.force and r["result"]["score"] <= max(p["score"] for p in prev):
            repeats.append(r["symbol"])
            continue
        alerts.append(r)
    at = now().isoformat(timespec="seconds")
    for r in alerts:
        with ALERTS.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": at, "symbol": r["symbol"], "score": r["result"]["score"],
                                "fired": r["result"]["fired"]}, ensure_ascii=False) + "\n")
    near = [r for r in rows if not r["result"]["passes"] and len(r["result"]["fired"]) == c["min_flags"] - 1]
    sources = {"universe": src, "spot": [v for v, _ in ctx["spot"]], "derivs": ctx["derivs"]["venue"],
               "exchange_reserves": ctx["cex"].get("exchanges"), "trending": bool(ctx["trending"]),
               "errors": STATS["errors"]}
    run = {"at": at, "coins": len(rows), "dropped": dropped, "alerts_count": len(alerts), "sources": sources,
           "duration_s": round(time.time() - t0), "requests": STATS["requests"], "rows": rows}
    RUNS.mkdir(parents=True, exist_ok=True)
    rp = RUNS / f"{at[:16].replace(':', '')}.json"
    write_json(rp, run)
    for old in sorted(RUNS.glob("*.json"))[:-200]:
        old.unlink()
    out({"ok": True, "at": at, "coins_screened": len(rows), "dropped": dropped, "sources": sources,
         "duration_s": run["duration_s"], "run_file": str(rp.relative_to(ROOT)),
         "alerts": alerts, "skipped_repeats": repeats,
         "near": [{"symbol": r["symbol"], "fired": r["result"]["fired"], "score": r["result"]["score"]} for r in near],
         "top_volume": sorted(({"symbol": r["symbol"], "ratio": r["volume"].get("ratio"), "z": r["volume"].get("z")}
                               for r in rows if r["volume"].get("ratio")), key=lambda v: -v["ratio"])[:10]})


def cmd_coin(a):
    c = cfg()
    sym = a.symbol.upper()
    coins, _, src = universe(dict(c, top_n=250, min_market_cap=0, exclude_symbols=[]))
    x = next((k for k in coins if k["symbol"] == sym), None)
    if not x:
        out({"ok": False, "error": f"{sym} is not in the top 250 by market cap"}, 1)
    ctx = context_data(c, True)
    m = analyse(c, x, ctx, True)
    if m["onchain"].get("note", "").startswith("checked only"):
        m["flags"]["onchain"], m["onchain"] = onchain_coin(c, x, ctx["contracts"])
        if m["social"]["news"] is None:
            m["social"]["news"] = news_ratio(x["name"], sym)
        m["result"] = score(c, m["flags"])
    out({"ok": True, "at": now().isoformat(timespec="seconds"), "sources_errors": STATS["errors"], **m})


def cmd_config(a):
    c = read_json(CONFIG, {})
    if a.action == "show":
        out({"ok": True, "config": cfg(), "changed_from_default": c})
    if a.action == "reset":
        write_json(CONFIG, {})
        out({"ok": True, "config": cfg()})
    key, raw = a.key, a.value
    if key is None or raw is None:
        out({"ok": False, "error": "config set needs a key and a value"}, 1)
    if key.startswith("weights."):
        f = key.split(".", 1)[1]
        if f not in FLAGS:
            out({"ok": False, "error": f"unknown flag {f}", "flags": FLAGS}, 1)
        c.setdefault("weights", {})[f] = float(raw)
    elif key in DEFAULTS:
        d = DEFAULTS[key]
        try:
            val = (raw.lower() in ("1", "true", "yes", "да")) if isinstance(d, bool) else \
                  [s.strip() for s in raw.split(",") if s.strip()] if isinstance(d, list) else type(d)(float(raw)) \
                  if isinstance(d, (int, float)) else raw
        except ValueError:
            out({"ok": False, "error": f"bad value for {key}"}, 1)
        c[key] = val
    else:
        out({"ok": False, "error": f"unknown key {key}", "keys": list(DEFAULTS)}, 1)
    if c.get("min_flags") and not 1 <= c["min_flags"] <= len(FLAGS):
        out({"ok": False, "error": f"min_flags must be 1..{len(FLAGS)}"}, 1)
    write_json(CONFIG, c)
    out({"ok": True, "set": {key: raw}, "config": cfg()})


def cmd_alerts(a):
    rows = [json.loads(l) for l in ALERTS.read_text().splitlines()] if ALERTS.exists() else []
    since = (now() - timedelta(days=a.days)).isoformat()
    rows = [r for r in rows if r["at"] >= since]
    by = {}
    for r in rows:
        by[r["symbol"]] = by.get(r["symbol"], 0) + 1
    out({"ok": True, "days": a.days, "count": len(rows), "by_coin": by, "alerts": rows[-50:]})


def cmd_followup(a):
    """What happened to the price after each alert: price at the alert (from its run file) vs now."""
    rows = [json.loads(l) for l in ALERTS.read_text().splitlines()] if ALERTS.exists() else []
    since = (now() - timedelta(days=a.days)).isoformat()
    rows = [r for r in rows if r["at"] >= since]
    if not rows:
        out({"ok": True, "days": a.days, "alerts": [], "note": "no alerts in this period"})
    coins, _, _ = universe(dict(cfg(), top_n=250, min_market_cap=0, exclude_symbols=[]))
    price_now = {x["symbol"]: x["price"] for x in coins}
    res = []
    for r in rows:
        f = RUNS / f"{r['at'][:16].replace(':', '')}.json"
        run = read_json(f, {})
        row = next((x for x in run.get("rows", []) if x["symbol"] == r["symbol"]), None)
        p0, p1 = (row or {}).get("price"), price_now.get(r["symbol"])
        res.append({"at": r["at"], "symbol": r["symbol"], "score": r["score"], "fired": r["fired"], "price_at_alert": p0,
                    "price_now": p1, "change_pct": rnd((p1 / p0 - 1) * 100) if p0 and p1 else None,
                    "regime": ((row or {}).get("derivs") or {}).get("regime")})
    moved = [x["change_pct"] for x in res if x["change_pct"] is not None]
    out({"ok": True, "days": a.days, "alerts": res,
         "summary": {"count": len(res), "median_abs_move_pct": rnd(statistics.median([abs(m) for m in moved])) if moved else None,
                     "up": sum(1 for m in moved if m > 0), "down": sum(1 for m in moved if m < 0)},
         "note": "An alert is an anomaly, not a direction call: a big move either way means it caught something."})


def cmd_sources(a):
    checks = {
        "coingecko": ("https://api.coingecko.com/api/v3/ping", None),
        "coinpaprika": ("https://api.coinpaprika.com/v1/global", None),
        "binance_spot": ("https://api.binance.com/api/v3/ping", None),
        "binance_futures": ("https://fapi.binance.com/fapi/v1/ping", None),
        "bybit": ("https://api.bybit.com/v5/market/time", None),
        "okx": ("https://www.okx.com/api/v5/public/time", None),
        "hyperliquid": ("https://api.hyperliquid.xyz/info", {"type": "meta"}),
        "defillama": ("https://coins.llama.fi/prices/current/coingecko:bitcoin", None),
        "blockscout": ("https://eth.blockscout.com/api/v2/stats", None),
        "gdelt": ("https://api.gdeltproject.org/api/v2/doc/doc?query=bitcoin&mode=timelinevolraw&format=json&timespan=1d", None),
    }
    res = {}
    for name, (url, body) in checks.items():
        try:
            r = http(url, data=body, tries=1, timeout=30)
            res[name] = "ok" if r is not None else f"error ({STATS['errors'].get(urllib.parse.urlparse(url).netloc, 'no data')})"
        except Blocked as e:
            res[name] = f"blocked from this server ({e})"
    out({"ok": True, "sources": res,
         "note": "Binance blocked -> Bybit, then OKX/Hyperliquid are used automatically; GDELT allows one request per 5 s."})


def cmd_report_path(a):
    topic = re.sub(r"[^\w-]+", "-", a.topic.lower()).strip("-")[:60] or "report"
    REPORTS.mkdir(parents=True, exist_ok=True)
    out({"ok": True, "path": str((REPORTS / f"{now().date().isoformat()}-{topic}.md").relative_to(ROOT))})


def main():
    ap = argparse.ArgumentParser(description="Anomalous volume screener")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("context").set_defaults(func=cmd_context)
    p = sub.add_parser("run"); p.add_argument("--top", type=int); p.add_argument("--no-slow", action="store_true")
    p.add_argument("--force", action="store_true", help="ignore the cooldown"); p.set_defaults(func=cmd_run)
    p = sub.add_parser("coin"); p.add_argument("symbol"); p.set_defaults(func=cmd_coin)
    p = sub.add_parser("config"); p.add_argument("action", choices=["show", "set", "reset"]); p.add_argument("key", nargs="?")
    p.add_argument("value", nargs="?"); p.set_defaults(func=cmd_config)
    p = sub.add_parser("alerts"); p.add_argument("--days", type=int, default=7); p.set_defaults(func=cmd_alerts)
    p = sub.add_parser("followup"); p.add_argument("--days", type=int, default=7); p.set_defaults(func=cmd_followup)
    sub.add_parser("sources").set_defaults(func=cmd_sources)
    p = sub.add_parser("report-path"); p.add_argument("topic"); p.set_defaults(func=cmd_report_path)
    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
