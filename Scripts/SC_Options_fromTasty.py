# ##############################################################################
# tastytrade options dump: next 8 expiries, 0.10-0.30 |delta| band.
#
# Reads tickers from User_Files\Tracklist.csv (Tickers column).
# Credentials (comments allowed) outside git:
#   Automation_Not_in_Git\TastyStuff.txt
#     client id, client secret, refresh token
#
# Streams DXLink Greeks for every strike on those 8 expiries (no IV
# strike window). Unsubscribes each batch after greeks land. REST fills
# option quotes for the contracts that pass the delta band.
#
# Also writes Ticker-metrics: one row per underlying from GET
# /market-metrics. Days_To_Earnings is +days to expected-report-date,
# or -days since last historic earnings-reports date if no expected.
# Notes sheet explains column headers. Ticker sheets drop LocalSymbol
# and Abs_Delta (|delta| is still used internally for the band and Summary).
#
# No TWS. OAuth + nested chain + DXLink greeks + REST option quotes.
#
# Run from the scripts directory:
#   python SC_Options_fromTasty.py
#
# Output:
#   Automation_Not_in_Git\Logs\YYYY-MM-DD-HH-MM-SS-Options_from_Tasty.xlsx
# ##############################################################################

import asyncio
import datetime as dt
import json
import logging
import os
import sys
import time
import traceback
from datetime import date, datetime
from urllib.parse import quote

import pandas as pd
import requests
import websockets
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.styles.colors import Color
from openpyxl.utils import get_column_letter
from zoneinfo import ZoneInfo

dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
log_dir = "\\..\\..\\..\\Automation_Not_in_Git\\" + "Logs"
log_dir_full = os.path.normpath(dir_path + log_dir)
os.makedirs(log_dir_full, exist_ok=True)

tracklist_path = os.path.normpath(dir_path + user_dir + "\\Tracklist.csv")
cred_path = os.path.normpath(
  dir_path + "\\..\\..\\..\\Automation_Not_in_Git\\TastyStuff.txt"
)

BASE = "https://api.tastyworks.com"
UA = "SC_Options_fromTasty/1.0"
WEEKLY_COUNT = 8
DELTA_LO = 0.10
DELTA_HI = 0.30
GREEKS_WAIT_S = 15
GREEKS_IDLE_S = 5
GREEKS_BATCH = 40
QUOTE_BATCH = 80
METRICS_BATCH = 40
EARNINGS_LOOKBACK_DAYS = 400
BLANK_COL = " "
TICKER_METRIC_COLS = [
  "Ticker",
  "Days_To_Earnings",
  "implied-volatility-index",
  "implied-volatility-index-rank",
  "implied-volatility-percentile",
  "implied-volatility-30-day",
  "iv-hv-30-day-difference",
  "implied-volatility-index-5-day-change",
  BLANK_COL,
  "implied-volatility-index-15-day",
  "historical-volatility-30-day",
  "historical-volatility-60-day",
  "historical-volatility-90-day",
]
INDEX_PCT_COLS = {
  "implied-volatility-index",
  "implied-volatility-index-5-day-change",
  "implied-volatility-index-15-day",
}
RANK_PCT_COLS = {
  "implied-volatility-index-rank",
  "implied-volatility-percentile",
}
TICKER_DROP_COLS = ("Abs_Delta", "LocalSymbol")
NOTES_SECTIONS = ("Ticker-metrics", "Summary", "Ticker sheet")

CENTER = Alignment(horizontal="center", vertical="center")
HEADER_FONT = Font(name="Calibri", size=11, bold=True)
HEADER_FILL = PatternFill(
  fill_type="solid",
  fgColor=Color(theme=7, tint=0.5999938962981048),
)
HEADER_BORDER = Border(
  left=Side(style="thin"),
  right=Side(style="thin"),
  top=Side(style="thin"),
  bottom=Side(style="thin"),
)
SECTION_FILL = PatternFill(start_color="D9EAD3", end_color="D9EAD3", fill_type="solid")
SECTION_SIDE = Side(style="medium", color="6B8F71")
SECTION_BORDER = Border(
  left=SECTION_SIDE,
  right=SECTION_SIDE,
  top=SECTION_SIDE,
  bottom=SECTION_SIDE,
)
CALL_FONT = Font(color="C00000")
PUT_FONT = Font(color="006600")
CALL_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
PUT_FILL = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
COL_MIN_WIDTH = {
  "Underlying": 12,
  "Underlying_Price": 18,
  "Expiry": 14,
  "DTE": 8,
  "Type": 10,
  "Strike": 10,
  "Delta": 10,
  "IV": 8,
  "IVx": 8,
  "Gamma": 9,
  "Last": 10,
  "Close": 10,
  "Mark": 10,
  "Volume": 10,
  "Open_Interest": 16,
  "Moneyness": 14,
  "Ticker": 10,
  "C30_K": 10,
  "C30_IV": 10,
  "P30_K": 10,
  "P30_IV": 10,
  "C10_K": 10,
  "C10_IV": 10,
  "P10_K": 10,
  "P10_IV": 10,
}

logging.basicConfig(
  level=logging.DEBUG,
  format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
  datefmt="%m-%d %H:%M",
  filename=os.path.join(log_dir_full, "SC_Options_fromTasty_debug.txt"),
  filemode="w",
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("%(name)-12s: %(levelname)-8s %(message)s"))
logging.getLogger("").addHandler(console)
logging.disable(sys.maxsize)
logging.disable(logging.NOTSET)


def _output_path():
  stamp = dt.datetime.now(ZoneInfo("America/New_York")).strftime(
    "%Y-%m-%d-%H-%M-%S"
  )
  return os.path.join(log_dir_full, stamp + "-Options_from_Tasty.xlsx")


def finite(x):
  try:
    if x is None:
      return False
    f = float(x)
    return f == f and f not in (-1,)
  except Exception:
    return False


def sheet_name(ticker):
  bad = set("\\/*?:[]")
  name = "".join(ch for ch in str(ticker) if ch not in bad).strip() or "TICKER"
  return name[:31]


def iv_as_pct(iv):
  if not finite(iv):
    return None
  iv = float(iv)
  if iv < 5:
    return iv * 100.0
  return iv


def norm_symbol(sym):
  s = "" if sym is None else str(sym).strip().upper()
  s = s.replace(" ", "").replace("/", ".").replace("-", ".")
  return s


def tasty_symbol(ticker):
  t = str(ticker).strip().upper()
  if "." in t:
    return t.replace(".", "/")
  return t


def parse_ymd(val):
  if val is None:
    return None
  s = str(val).strip()
  if not s or s.lower() == "nan":
    return None
  try:
    return datetime.strptime(s[:10], "%Y-%m-%d").date()
  except ValueError:
    return None


def to_float(val):
  try:
    if val is None:
      return None
    f = float(val)
    if f != f:
      return None
    return f
  except Exception:
    return None


def index_as_pct(val):
  f = to_float(val)
  if f is None:
    return None
  if abs(f) <= 3:
    return f * 100.0
  return f


def rank_as_pct(val):
  f = to_float(val)
  if f is None:
    return None
  return f * 100.0


def load_creds():
  lines = []
  for ln in open(cred_path, encoding="utf-8"):
    ln = ln.strip()
    if not ln or ln.startswith("#"):
      continue
    lines.append(ln)
  if len(lines) < 3:
    raise SystemExit(
      "TastyStuff.txt needs client_id, client_secret, refresh_token (# comments ok)"
    )
  return lines[0], lines[1], lines[2]


def load_tickers():
  if len(sys.argv) > 1:
    seen = []
    for item in sys.argv[1:]:
      ticker = str(item).replace(" ", "").upper()
      if ticker and ticker not in seen:
        seen.append(ticker)
    return seen
  tracklist_df = pd.read_csv(tracklist_path)
  seen = []
  for item in tracklist_df["Tickers"].tolist():
    if str(item) == "nan":
      continue
    ticker = str(item).replace(" ", "").upper()
    if ticker and ticker not in seen:
      seen.append(ticker)
  return seen


def _style_sheet(ws, moneyness_as_pct=False, color_by_type=False, delta_as_pct=False, freeze="A2"):
  headers = [cell.value for cell in ws[1]]
  col_index = {name: i + 1 for i, name in enumerate(headers) if name}
  type_col = col_index.get("Type")
  money_col = col_index.get("Moneyness")
  pct_suffix_cols = []
  for name in (
    "IVx", "IV", "C30_IV", "P30_IV", "C10_IV", "P10_IV",
  ):
    if name in col_index:
      pct_suffix_cols.append(col_index[name])
  gamma_col = col_index.get("Gamma")
  delta_cols = []
  if delta_as_pct:
    for name in ("Delta", "Abs_Delta", "C30_d", "P30_d", "C10_d", "P10_d"):
      if name in col_index:
        delta_cols.append(col_index[name])

  for cell in ws[1]:
    cell.alignment = CENTER
    cell.font = HEADER_FONT
    cell.fill = HEADER_FILL
    cell.border = HEADER_BORDER
  ws.freeze_panes = freeze

  for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
    kind = ""
    if type_col:
      kind = str(row[type_col - 1].value or "").strip().lower()
    for cell in row:
      cell.alignment = CENTER
      if (
        moneyness_as_pct
        and money_col
        and cell.column == money_col
        and isinstance(cell.value, (int, float))
      ):
        cell.number_format = "0.00%"
      if cell.column in delta_cols and isinstance(cell.value, (int, float)):
        cell.number_format = '0.00"%"'
      if cell.column in pct_suffix_cols and isinstance(cell.value, (int, float)):
        cell.number_format = '0.00"%"'
      if gamma_col and cell.column == gamma_col and isinstance(cell.value, (int, float)):
        cell.number_format = "0.000"
      if color_by_type and kind == "call" and cell.column in (type_col, money_col):
        cell.font = CALL_FONT
        cell.fill = CALL_FILL
      elif color_by_type and kind == "put" and cell.column in (type_col, money_col):
        cell.font = PUT_FONT
        cell.fill = PUT_FILL

  for idx, name in enumerate(headers, start=1):
    letter = get_column_letter(idx)
    max_len = len(str(name or ""))
    for col_cells in ws.iter_rows(min_row=2, min_col=idx, max_col=idx, max_row=ws.max_row):
      cell = col_cells[0]
      val = cell.value
      if val is None:
        text = ""
      elif cell.number_format == "0.00%" and isinstance(val, (int, float)):
        text = "{:.2f}%".format(val * 100.0)
      elif cell.number_format == '0.00"%"' and isinstance(val, (int, float)):
        text = "{:.2f}%".format(val)
      elif cell.number_format == "0.00" and isinstance(val, (int, float)):
        text = "{:.2f}".format(val)
      elif cell.number_format == "0.000" and isinstance(val, (int, float)):
        text = "{:.3f}".format(val)
      else:
        text = str(val)
      if len(text) > max_len:
        max_len = len(text)
    pad = 1 if name in ("IVx", "IV", "Gamma") else 3
    width = max(COL_MIN_WIDTH.get(name, 12), max_len + pad)
    ws.column_dimensions[letter].width = min(width, 42)


class TastyRest:
  def __init__(self, client_id, client_secret, refresh_token):
    self.client_id = client_id
    self.client_secret = client_secret
    self.refresh_token = refresh_token
    self.access = None
    self.access_exp = 0.0
    self.dx_token = None
    self.dx_url = None

  def ensure_access(self):
    if self.access and time.time() < self.access_exp - 60:
      return
    r = requests.post(
      BASE + "/oauth/token",
      headers={"User-Agent": UA, "Content-Type": "application/json"},
      json={
        "grant_type": "refresh_token",
        "refresh_token": self.refresh_token,
        "client_secret": self.client_secret,
        "client_id": self.client_id,
      },
      timeout=30,
    )
    if r.status_code != 200:
      raise RuntimeError("oauth failed " + str(r.status_code) + " " + r.text[:200])
    tok = r.json()
    self.access = tok["access_token"]
    self.access_exp = time.time() + float(tok.get("expires_in") or 900)
    logging.info("tastytrade access token ok  expires_in=" + str(tok.get("expires_in")))

  def headers(self):
    self.ensure_access()
    return {
      "Authorization": "Bearer " + self.access,
      "User-Agent": UA,
      "Accept": "application/json",
    }

  def get(self, path, **kwargs):
    r = requests.get(BASE + path, headers=self.headers(), timeout=30, **kwargs)
    r.raise_for_status()
    return r.json()

  def nested_chain(self, symbol):
    payload = self.get("/option-chains/" + symbol + "/nested")
    items = (payload.get("data") or {}).get("items") or []
    return items[0] if items else None

  def equity_quote(self, symbol):
    payload = self.get("/market-data/by-type", params={"equity": symbol})
    items = (payload.get("data") or {}).get("items") or []
    return items[0] if items else None

  def option_quotes(self, occ_symbols):
    out = {}
    for i in range(0, len(occ_symbols), QUOTE_BATCH):
      batch = occ_symbols[i:i + QUOTE_BATCH]
      payload = self.get(
        "/market-data/by-type",
        params={"equity-option": ",".join(batch)},
      )
      for it in (payload.get("data") or {}).get("items") or []:
        out[it.get("symbol")] = it
    return out

  def market_metrics(self, tickers):
    by_norm = {}
    n = len(tickers)
    logging.info("tastytrade market-metrics: " + str(n) + " symbols")
    for i in range(0, n, METRICS_BATCH):
      chunk = tickers[i:i + METRICS_BATCH]
      syms = ",".join(tasty_symbol(t) for t in chunk)
      try:
        r = requests.get(
          BASE + "/market-metrics",
          params={"symbols": syms},
          headers=self.headers(),
          timeout=60,
        )
        if r.status_code != 200:
          logging.error(
            "metrics batch " + str(i) + " HTTP " + str(r.status_code)
            + " " + r.text[:160]
          )
          continue
        items = (r.json().get("data") or {}).get("items") or []
        for it in items:
          by_norm[norm_symbol(it.get("symbol"))] = it
        logging.info(
          "metrics " + str(min(i + METRICS_BATCH, n)) + "/" + str(n)
          + "  got=" + str(len(items))
        )
      except Exception as exc:
        logging.error("metrics batch " + str(i) + " " + str(exc))
    return by_norm

  def last_earnings_date(self, ticker, today):
    tasty = tasty_symbol(ticker)
    start = (today - dt.timedelta(days=EARNINGS_LOOKBACK_DAYS)).isoformat()
    path = (
      "/market-metrics/historic-corporate-events/earnings-reports/"
      + quote(tasty, safe="")
    )
    try:
      r = requests.get(
        BASE + path,
        headers=self.headers(),
        params={"start-date": start, "end-date": today.isoformat()},
        timeout=30,
      )
      if r.status_code != 200:
        logging.warning(
          ticker + " historic earnings HTTP " + str(r.status_code)
        )
        return None
      items = (r.json().get("data") or {}).get("items") or []
    except Exception as exc:
      logging.warning(ticker + " historic earnings " + str(exc))
      return None
    dates = []
    for it in items:
      d = parse_ymd((it or {}).get("occurred-date"))
      if d is not None and d <= today:
        dates.append(d)
    return max(dates) if dates else None

  def quote_token(self):
    payload = self.get("/api-quote-tokens")
    data = payload.get("data") or {}
    self.dx_token = data.get("token")
    self.dx_url = data.get("dxlink-url")
    if not self.dx_token or not self.dx_url:
      raise RuntimeError("no dxlink token")
    logging.debug("dxlink-url " + str(self.dx_url))
    return self.dx_url, self.dx_token


def pick_expiries(expirations, today):
  future = []
  fridays = []
  for e in expirations:
    try:
      d = datetime.strptime(str(e.get("expiration-date")), "%Y-%m-%d").date()
    except ValueError:
      continue
    if d < today:
      continue
    future.append(e)
    if d.weekday() == 4:
      fridays.append(e)
  chosen = fridays[:WEEKLY_COUNT]
  if len(chosen) < WEEKLY_COUNT:
    for e in future:
      if e not in chosen:
        chosen.append(e)
      if len(chosen) >= WEEKLY_COUNT:
        break
  return chosen


def _store_greek(greeks, sym, price, vol, delta, gamma, theta, vega):
  if not isinstance(sym, str) or not sym:
    return
  greeks[sym] = {
    "price": price,
    "volatility": vol,
    "delta": delta,
    "gamma": gamma,
    "theta": theta,
    "vega": vega,
  }


def _parse_greeks_compact(item, greeks):
  if not isinstance(item, list):
    return
  # One record: ["Greeks", ".HOOD...", price, vol, delta, gamma, theta, vega]
  # or a flat concatenation of those records in a single array.
  i = 0
  n = len(item)
  while i < n:
    if item[i] == "Greeks" and i + 7 < n:
      _store_greek(
        greeks,
        item[i + 1],
        item[i + 2],
        item[i + 3],
        item[i + 4],
        item[i + 5],
        item[i + 6],
        item[i + 7],
      )
      i += 8
      continue
    if isinstance(item[i], str) and item[i].startswith(".") and i + 6 < n:
      _store_greek(
        greeks,
        item[i],
        item[i + 1],
        item[i + 2],
        item[i + 3],
        item[i + 4],
        item[i + 5],
        item[i + 6],
      )
      i += 7
      continue
    i += 1


def parse_feed_data(data, greeks, quotes, summaries):
  cur = None
  for item in data:
    if isinstance(item, str):
      cur = item
      continue
    if not isinstance(item, list) or not cur:
      continue
    if cur == "Greeks":
      _parse_greeks_compact(item, greeks)
      continue
    if len(item) < 2:
      continue
    sym = item[1]
    if cur == "Quote" and len(item) >= 4:
      quotes[sym] = {"bid": item[2], "ask": item[3]}
    elif cur == "Summary" and len(item) >= 3:
      summaries[sym] = {
        "openInterest": item[2],
        "prevClose": item[3] if len(item) > 3 else None,
      }


async def _dx_recv(ws, greeks, quotes, summaries, timeout):
  try:
    raw = await asyncio.wait_for(ws.recv(), timeout=max(0.05, timeout))
  except asyncio.TimeoutError:
    return None
  msg = json.loads(raw)
  kind = msg.get("type")
  if kind == "FEED_DATA":
    parse_feed_data(msg.get("data") or [], greeks, quotes, summaries)
  elif kind == "KEEPALIVE":
    await ws.send(json.dumps({"type": "KEEPALIVE", "channel": 0}))
  return msg


async def _subscribe_greeks(ws, symbols, reset):
  first = True
  for i in range(0, len(symbols), GREEKS_BATCH):
    batch = symbols[i:i + GREEKS_BATCH]
    add = [{"type": "Greeks", "symbol": s} for s in batch]
    sub = {"type": "FEED_SUBSCRIPTION", "channel": 1, "add": add}
    if reset and first:
      sub["reset"] = True
      first = False
    await ws.send(json.dumps(sub))


async def _unsubscribe_greeks(ws, symbols):
  for i in range(0, len(symbols), GREEKS_BATCH):
    batch = symbols[i:i + GREEKS_BATCH]
    rem = [{"type": "Greeks", "symbol": s} for s in batch]
    await ws.send(json.dumps({
      "type": "FEED_SUBSCRIPTION",
      "channel": 1,
      "remove": rem,
    }))


async def _wait_greeks(ws, greeks, quotes, summaries, wanted, wait_s):
  wanted_set = set(wanted)
  n_want = len(wanted_set)
  started = time.monotonic()
  hard_end = started + float(wait_s)
  min_end = started + 8.0
  last_n = sum(1 for s in wanted_set if s in greeks)
  last_new = started
  while time.monotonic() < hard_end:
    have = sum(1 for s in wanted_set if s in greeks)
    if have >= n_want:
      return have
    await _dx_recv(
      ws, greeks, quotes, summaries, min(1.0, hard_end - time.monotonic())
    )
    n = sum(1 for s in wanted_set if s in greeks)
    now = time.monotonic()
    if n > last_n:
      last_n = n
      last_new = now
    elif n > 0 and now >= min_end and (now - last_new) >= GREEKS_IDLE_S:
      break
  return sum(1 for s in wanted_set if s in greeks)


async def stream_option_data(dx_url, dx_token, symbol_groups, wait_s):
  greeks, quotes, summaries = {}, {}, {}
  groups = [list(dict.fromkeys(g)) for g in symbol_groups if g]
  if not groups:
    return greeks, quotes, summaries
  async with websockets.connect(dx_url, open_timeout=20) as ws:
    await ws.send(json.dumps({
      "type": "SETUP",
      "channel": 0,
      "version": "0.1-DXF-JS/0.3.0",
      "keepaliveTimeout": 60,
      "acceptKeepaliveTimeout": 60,
    }))
    ready = False
    handshake_end = time.monotonic() + 15
    while time.monotonic() < handshake_end and not ready:
      msg = await _dx_recv(ws, greeks, quotes, summaries, handshake_end - time.monotonic())
      if not msg:
        continue
      kind = msg.get("type")
      if kind == "AUTH_STATE" and msg.get("state") == "UNAUTHORIZED":
        await ws.send(json.dumps({"type": "AUTH", "channel": 0, "token": dx_token}))
      elif kind == "AUTH_STATE" and msg.get("state") == "AUTHORIZED":
        await ws.send(json.dumps({
          "type": "CHANNEL_REQUEST",
          "channel": 1,
          "service": "FEED",
          "parameters": {"contract": "AUTO"},
        }))
      elif kind == "CHANNEL_OPENED":
        await ws.send(json.dumps({
          "type": "FEED_SETUP",
          "channel": 1,
          "acceptAggregationPeriod": 0.1,
          "acceptDataFormat": "COMPACT",
          "acceptEventFields": {
            "Greeks": [
              "eventType", "eventSymbol", "price", "volatility",
              "delta", "gamma", "theta", "vega",
            ],
          },
        }))
      elif kind == "FEED_CONFIG":
        ready = True

    for gi, group in enumerate(groups):
      await _subscribe_greeks(ws, group, reset=(gi == 0))
      await _dx_recv(ws, greeks, quotes, summaries, 0.3)
      got = await _wait_greeks(ws, greeks, quotes, summaries, group, wait_s)
      logging.info(
        "greeks expiry " + str(gi + 1) + "/" + str(len(groups))
        + " got=" + str(got) + "/" + str(len(group))
      )
      try:
        await _unsubscribe_greeks(ws, group)
      except Exception as exc:
        logging.debug("unsubscribe expiry " + str(gi + 1) + " " + str(exc))
  return greeks, quotes, summaries


def candidate_contracts(exp_obj):
  dte = int(exp_obj.get("days-to-expiration") or 0)
  out = []
  for s in exp_obj.get("strikes") or []:
    try:
      k = float(s.get("strike-price"))
    except (TypeError, ValueError):
      continue
    if s.get("call") and s.get("call-streamer-symbol"):
      out.append(("C", k, s["call"], s["call-streamer-symbol"]))
    if s.get("put") and s.get("put-streamer-symbol"):
      out.append(("P", k, s["put"], s["put-streamer-symbol"]))
  return out, dte


async def pull_ticker(api, symbol, dx_url, dx_token):
  q = api.equity_quote(symbol)
  spot = None
  if q:
    for key in ("last", "mark", "close", "prev-close"):
      if finite(q.get(key)):
        spot = float(q.get(key))
        break
  logging.info(symbol + " last=" + str(q.get("last") if q else None) + " spot=" + str(spot))
  if spot is None:
    return pd.DataFrame(), None

  chain = api.nested_chain(symbol)
  if not chain:
    logging.warning(symbol + ": no option chain")
    return pd.DataFrame(), spot
  expiries = pick_expiries(chain.get("expirations") or [], date.today())
  logging.info(symbol + " expiries=" + str(len(expiries)))

  all_cands = []
  groups = []
  for exp_obj in expiries:
    exp_date = str(exp_obj.get("expiration-date"))
    cands, dte = candidate_contracts(exp_obj)
    logging.info(symbol + " " + exp_date + " quoted " + str(len(cands)) + " contracts")
    for right, strike, occ, stream in cands:
      all_cands.append((exp_date, dte, right, strike, occ, stream))
    groups.append([c[3] for c in cands])

  streamer_n = sum(len(g) for g in groups)
  try:
    greeks, dx_quotes, summaries = await stream_option_data(
      dx_url, dx_token, groups, GREEKS_WAIT_S
    )
  except Exception as exc:
    logging.error(symbol + " stream failed: " + str(exc))
    logging.debug(traceback.format_exc())
    greeks, dx_quotes, summaries = {}, {}, {}
  logging.info(
    symbol + " greeks=" + str(len(greeks)) + "/" + str(streamer_n)
    + " dx_quotes=" + str(len(dx_quotes))
  )

  kept_meta = []
  for exp_date, dte, right, strike, occ, stream in all_cands:
    g = greeks.get(stream)
    if not g or not finite(g.get("delta")):
      continue
    delta = float(g["delta"])
    ad = abs(delta)
    if ad < DELTA_LO or ad > DELTA_HI:
      continue
    kept_meta.append((exp_date, dte, right, strike, occ, stream, g, delta, ad))

  occs = [m[4] for m in kept_meta]
  rest_quotes = {}
  if occs:
    try:
      rest_quotes = api.option_quotes(occs)
    except Exception as exc:
      logging.debug(symbol + " REST quotes failed: " + str(exc))

  rows = []
  kept_by_exp = {}
  for exp_date, dte, right, strike, occ, stream, g, delta, ad in kept_meta:
    rq = rest_quotes.get(occ) or {}
    dq = dx_quotes.get(stream) or {}
    sm = summaries.get(stream) or {}
    last = rq.get("last")
    close = rq.get("close") or rq.get("prev-close") or sm.get("prevClose")
    mark = rq.get("mark")
    if not finite(mark):
      bid, ask = dq.get("bid"), dq.get("ask")
      if finite(bid) and finite(ask):
        mark = (float(bid) + float(ask)) / 2.0
      elif finite(g.get("price")):
        mark = g.get("price")
    vol = rq.get("volume")
    oi = rq.get("open-interest")
    if not finite(oi):
      oi = sm.get("openInterest")
    und_px = spot
    if right == "C":
      mny = (und_px - strike) / und_px
    else:
      mny = (strike - und_px) / und_px
    rows.append({
      "Underlying": symbol,
      "Underlying_Price": und_px,
      "Expiry": exp_date,
      "DTE": dte,
      "Type": "Call" if right == "C" else "Put",
      "Strike": strike,
      "Delta": delta,
      "Abs_Delta": ad,
      "IV": iv_as_pct(g.get("volatility")),
      "Gamma": float(g["gamma"]) if finite(g.get("gamma")) else None,
      "Last": float(last) if finite(last) else None,
      "Close": float(close) if finite(close) else None,
      "Mark": float(mark) if finite(mark) else None,
      "Volume": float(vol) if finite(vol) else None,
      "Open_Interest": float(oi) if finite(oi) else None,
      "Moneyness": mny,
      "LocalSymbol": occ,
    })
    kept_by_exp[exp_date] = kept_by_exp.get(exp_date, 0) + 1
  for exp_obj in expiries:
    exp_date = str(exp_obj.get("expiration-date"))
    logging.info(
      symbol + " " + exp_date + " kept "
      + str(kept_by_exp.get(exp_date, 0)) + " in 0.10-0.30 |delta|"
    )

  df = pd.DataFrame(rows)
  if not df.empty:
    df = df.sort_values(
      ["Expiry", "Type", "Abs_Delta"], ascending=[True, True, False]
    )
  return df, spot


def prepare_otm_df(df):
  out = df.copy()
  if out.empty:
    return out
  put_mask = out["Type"].astype(str).str.strip().str.lower() == "put"
  out.loc[put_mask, "Moneyness"] = -pd.to_numeric(
    out.loc[put_mask, "Moneyness"], errors="coerce"
  )
  out["Delta"] = pd.to_numeric(out["Delta"], errors="coerce") * 100.0
  return out


def ticker_sheet_df(df):
  otm = prepare_otm_df(df)
  if "IV" in otm.columns:
    otm = otm.rename(columns={"IV": "IVx"})
  otm = _sort_ticker_sheet(otm)
  otm = otm.drop(columns=list(TICKER_DROP_COLS), errors="ignore")
  return _with_group_blanks(otm, "Expiry")


def _sort_ticker_sheet(df):
  if df is None or df.empty:
    return df
  chunks = []
  for _, group in df.groupby("Expiry", sort=True, dropna=False):
    g_kind = group["Type"].astype(str).str.strip().str.lower()
    calls = group.loc[g_kind == "call"].sort_values(
      "Strike", ascending=False, kind="mergesort"
    )
    puts = group.loc[g_kind == "put"]
    other = group.loc[~g_kind.isin(["call", "put"])]
    chunks.append(pd.concat([calls, puts, other]))
  return pd.concat(chunks, ignore_index=True)


def _with_group_blanks(df, group_col):
  if df is None or df.empty or group_col not in df.columns:
    return df
  chunks = []
  groups = list(df.groupby(group_col, sort=False, dropna=False))
  blank = pd.DataFrame([{col: None for col in df.columns}])
  for i, (_, group) in enumerate(groups):
    chunks.append(group)
    if i < len(groups) - 1:
      chunks.append(blank)
  return pd.concat(chunks, ignore_index=True)


def nearest_band_row(g, target):
  if g.empty:
    return None
  i = (g["Abs_Delta"] - target).abs().idxmin()
  return g.loc[i]


def build_summary(frames):
  rows = []
  for ticker, df in frames.items():
    if df is None or df.empty:
      continue
    for exp, g in df.groupby("Expiry", sort=True):
      calls = g[g["Type"].astype(str).str.lower() == "call"]
      puts = g[g["Type"].astype(str).str.lower() == "put"]
      c30 = nearest_band_row(calls, 0.30)
      c10 = nearest_band_row(calls, 0.10)
      p30 = nearest_band_row(puts, 0.30)
      p10 = nearest_band_row(puts, 0.10)
      rows.append({
        "Ticker": ticker,
        "Expiry": exp,
        "DTE": int(g["DTE"].iloc[0]),
        "Underlying_Price": g["Underlying_Price"].iloc[0],
        "C30_K": None if c30 is None else c30["Strike"],
        "C30_d": None if c30 is None else c30["Delta"] * 100.0,
        "C30_IV": None if c30 is None else c30["IV"],
        "P30_K": None if p30 is None else p30["Strike"],
        "P30_d": None if p30 is None else p30["Delta"] * 100.0,
        "P30_IV": None if p30 is None else p30["IV"],
        "C10_K": None if c10 is None else c10["Strike"],
        "C10_d": None if c10 is None else c10["Delta"] * 100.0,
        "C10_IV": None if c10 is None else c10["IV"],
        "P10_K": None if p10 is None else p10["Strike"],
        "P10_d": None if p10 is None else p10["Delta"] * 100.0,
        "P10_IV": None if p10 is None else p10["IV"],
      })
  return pd.DataFrame(rows)


def format_ticker_got(ticker, df):
  if df is None or df.empty:
    return "Ticker " + ticker + " : no 0.10-0.30 delta rows"
  parts = []
  for exp, group in df.groupby("Expiry", sort=True):
    ymd = str(exp).replace("-", "/")
    parts.append("[expiry : " + ymd + ", got : " + str(len(group)) + "]")
  return "Ticker " + ticker + " : " + ", ".join(parts)


def metric_value(item, field):
  if not item:
    return None
  raw = item.get(field)
  if field in RANK_PCT_COLS:
    return rank_as_pct(raw)
  if field in INDEX_PCT_COLS:
    return index_as_pct(raw)
  return to_float(raw)


def earnings_days(ticker, item, api, today):
  earn = (item or {}).get("earnings") or {}
  expected = parse_ymd(earn.get("expected-report-date"))
  if expected is not None and expected >= today:
    days = (expected - today).days
    logging.info(
      ticker + " earnings expected=" + expected.isoformat()
      + " Days_To_Earnings=" + str(days)
    )
    return days
  last = api.last_earnings_date(ticker, today)
  if last is not None:
    days = (last - today).days
    logging.info(
      ticker + " earnings last=" + last.isoformat()
      + " Days_To_Earnings=" + str(days)
    )
    return days
  logging.info(ticker + " earnings none")
  return None


def build_ticker_metrics(tickers, metrics_by, api, today):
  rows = []
  for ticker in tickers:
    item = metrics_by.get(norm_symbol(ticker))
    row = {col: None for col in TICKER_METRIC_COLS}
    row["Ticker"] = ticker
    row["Days_To_Earnings"] = earnings_days(ticker, item, api, today)
    row[BLANK_COL] = None
    for col in TICKER_METRIC_COLS:
      if col in ("Ticker", "Days_To_Earnings", BLANK_COL):
        continue
      row[col] = metric_value(item, col)
    rows.append(row)
  return pd.DataFrame(rows, columns=TICKER_METRIC_COLS)


def _header_words(name):
  return str(name or "").replace("-", " ").replace("_", " ").replace("\n", " ").split()


def _wrap_header(name, width_chars):
  words = _header_words(name)
  if not words:
    return ""
  width_chars = max(int(width_chars), max(len(w) for w in words), 1)
  lines = [words[0]]
  for word in words[1:]:
    trial = lines[-1] + " " + word
    if len(trial) <= width_chars:
      lines[-1] = trial
    else:
      lines.append(word)
  return "\n".join(lines)


def _style_ticker_metrics(ws):
  wrap_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
  n = min(len(TICKER_METRIC_COLS), ws.max_column or 0)
  for idx in range(1, n + 1):
    orig = TICKER_METRIC_COLS[idx - 1]
    cell = ws.cell(1, idx)
    if orig.strip():
      cell.value = orig.replace("-", " ").replace("_", " ")
    cell.alignment = wrap_align
    cell.font = HEADER_FONT
    cell.fill = HEADER_FILL
    cell.border = HEADER_BORDER
  ws.freeze_panes = "B2"

  for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
    for cell in row:
      cell.alignment = CENTER
      if cell.column > n:
        continue
      name = TICKER_METRIC_COLS[cell.column - 1]
      if not isinstance(cell.value, (int, float)):
        continue
      if name == "Days_To_Earnings":
        cell.number_format = "0"
      elif name not in ("Ticker", BLANK_COL):
        cell.number_format = '0.00"%"'

  max_header_lines = 2
  for idx in range(1, n + 1):
    orig = TICKER_METRIC_COLS[idx - 1]
    letter = get_column_letter(idx)
    if orig is None or not str(orig).strip():
      ws.column_dimensions[letter].width = 3
      continue
    words = _header_words(orig)
    longest = max((len(w) for w in words), default=0)
    max_len = len("Ticker") if orig == "Ticker" else 0
    for col_cells in ws.iter_rows(
      min_row=2, min_col=idx, max_col=idx, max_row=ws.max_row
    ):
      cell = col_cells[0]
      val = cell.value
      if val is None:
        text = ""
      elif orig == "Ticker":
        text = str(val)
      elif orig == "Days_To_Earnings" and isinstance(val, (int, float)):
        text = "{:.0f}".format(val)
      elif isinstance(val, (int, float)):
        text = "{:.2f}%".format(val)
      else:
        text = str(val)
      if len(text) > max_len:
        max_len = len(text)
    # Fit the longest header word so wrap stays on word boundaries
    # ("earnings", "volatility", "historical") instead of a hanging letter.
    width = min(max(max_len + 2, longest + 2.5, 8), 16)
    ws.column_dimensions[letter].width = width
    wrapped = _wrap_header(orig, int(width))
    ws.cell(1, idx).value = wrapped
    lines = wrapped.count("\n") + 1 if wrapped else 1
    if lines > max_header_lines:
      max_header_lines = lines
  ws.row_dimensions[1].height = min(15 * max_header_lines + 8, 64)


def notes_df():
  rows = [
    (
      "Ticker-metrics",
      "One row per underlying from tasty GET /market-metrics. "
      "Index family and IVR/IVP are percent on the sheet (0.66 → 66.6). "
      "30d IV, HV, and IV-HV are already percent from tasty.",
    ),
    (
      "Days To Earnings",
      "Calendar days from today (America/New_York). Positive = days until "
      "tasty expected-report-date. If that date is missing or already past, "
      "negative = days since the latest historic earnings-reports date. "
      "Blank if neither exists.",
    ),
    (
      "implied volatility index",
      "tasty implied-volatility-index. VIX-style IV Index, ~30-day tenor. "
      "Sheet is percent.",
    ),
    (
      "implied volatility index rank",
      "tasty implied-volatility-index-rank (IVR). Where this name's Index "
      "sits in its own 52-week high-low range. Not the same as percentile. "
      "Can print above 100 or below 0 on a new high/low. Sheet is percent.",
    ),
    (
      "implied volatility percentile",
      "tasty implied-volatility-percentile (IVP). Share of the last ~252 "
      "sessions on which the Index was lower than now. Sheet is percent.",
    ),
    (
      "implied volatility 30 day",
      "tasty implied-volatility-30-day. Already a percent in the API.",
    ),
    (
      "iv hv 30 day difference",
      "tasty iv-hv-30-day-difference. 30d IV minus 30d HV, percent points. "
      "Positive = options pricing more vol than the stock just realized.",
    ),
    (
      "implied volatility index 5 day change",
      "tasty implied-volatility-index-5-day-change. Change in the Index over "
      "5 days. API is 0-1 units; sheet is percent points (0.028 → 2.80).",
    ),
    (
      "(blank)",
      "Spacer between the first metric group and the 15-day / HV group. "
      "No data.",
    ),
    (
      "implied volatility index 15 day",
      "tasty implied-volatility-index-15-day. 15-day tenor of the same Index "
      "(a level, not a change). Sheet is percent.",
    ),
    (
      "historical volatility 30 day",
      "tasty historical-volatility-30-day. 30-day realized / historical "
      "volatility. Already a percent.",
    ),
    (
      "historical volatility 60 day",
      "tasty historical-volatility-60-day. Already a percent.",
    ),
    (
      "historical volatility 90 day",
      "tasty historical-volatility-90-day. Already a percent.",
    ),
    (
      "Summary",
      "One row per ticker per expiry. Nearest call and put to |delta| 0.30 "
      "and 0.10 among the contracts kept in the 0.10-0.30 band.",
    ),
    (
      "C30_K",
      "Strike of the call whose |delta| is closest to 0.30 on that expiry.",
    ),
    (
      "C30_d",
      "That call's delta as a percent (25.00 means 0.25). Signed; calls are "
      "positive.",
    ),
    (
      "C30_IV",
      "Implied volatility of that ~0.30-delta call.",
    ),
    (
      "P30_K",
      "Strike of the put whose |delta| is closest to 0.30 on that expiry.",
    ),
    (
      "P30_d",
      "That put's delta as a percent. Signed; puts are negative.",
    ),
    (
      "P30_IV",
      "Implied volatility of that ~0.30-delta put.",
    ),
    (
      "C10_K",
      "Strike of the call whose |delta| is closest to 0.10 on that expiry.",
    ),
    (
      "C10_d",
      "That call's delta as a percent. Signed; calls are positive.",
    ),
    (
      "C10_IV",
      "Implied volatility of that ~0.10-delta call.",
    ),
    (
      "P10_K",
      "Strike of the put whose |delta| is closest to 0.10 on that expiry.",
    ),
    (
      "P10_d",
      "That put's delta as a percent. Signed; puts are negative.",
    ),
    (
      "P10_IV",
      "Implied volatility of that ~0.10-delta put.",
    ),
    (
      "Ticker sheet",
      "One sheet per underlying. Next 8 expiries. Contracts with |delta| "
      "0.10-0.30. Calls red, puts green on Type and Moneyness.",
    ),
    (
      "Moneyness",
      "(spot − strike) / spot, as a percent. Same formula for calls and puts. "
      "A call struck above spot is negative; a put struck below spot is "
      "positive. Rows on this sheet are usually OTM.",
    ),
    (
      "Delta",
      "Signed delta as a percent (14.10 means 0.141). Puts are negative. "
      "The sheet keeps 0.10-0.30 in |delta|.",
    ),
  ]
  return pd.DataFrame(rows, columns=["Column", "Detail"])


def _note_wrap_lines(text, width_chars):
  words = str(text or "").split()
  if not words:
    return 1
  width_chars = max(int(width_chars), 1)
  lines = 1
  cur = 0
  for word in words:
    add = len(word) if cur == 0 else len(word) + 1
    if cur + add <= width_chars:
      cur += add
    else:
      lines += 1
      cur = len(word)
  return lines


def _style_notes(ws):
  for cell in ws[1]:
    cell.alignment = CENTER
    cell.font = HEADER_FONT
    cell.fill = HEADER_FILL
    cell.border = HEADER_BORDER
  ws.freeze_panes = "A2"
  ws.column_dimensions["A"].width = 40
  ws.column_dimensions["B"].width = 92
  ws.row_dimensions[1].height = 18
  left_mid = Alignment(horizontal="left", vertical="center", wrap_text=True)
  left_top = Alignment(horizontal="left", vertical="top", wrap_text=True)
  left_one = Alignment(horizontal="left", vertical="center", wrap_text=False)
  for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=2):
    a, b = row[0], row[1]
    is_sec = str(a.value or "") in NOTES_SECTIONS
    lines = _note_wrap_lines(b.value, 86)
    if is_sec:
      a.font = HEADER_FONT
      b.font = HEADER_FONT
      a.fill = SECTION_FILL
      b.fill = SECTION_FILL
      a.border = SECTION_BORDER
      b.border = SECTION_BORDER
    if lines <= 1:
      a.alignment = left_one
      b.alignment = left_mid
      ws.row_dimensions[a.row].height = 18
    else:
      a.alignment = left_one
      b.alignment = left_top
      ws.row_dimensions[a.row].height = min(15 * lines + 4, 64)


def write_notes_sheet(wb):
  if "Notes" in wb.sheetnames:
    del wb["Notes"]
  ws = wb.create_sheet("Notes")
  df = notes_df()
  ws.cell(1, 1, "Column")
  ws.cell(1, 2, "Detail")
  for r, rec in enumerate(df.itertuples(index=False), start=2):
    ws.cell(r, 1, rec[0])
    ws.cell(r, 2, rec[1])
  _style_notes(ws)


def drop_ticker_display_cols(ws):
  headers = [cell.value for cell in ws[1]]
  for name in TICKER_DROP_COLS:
    if name not in headers:
      continue
    ws.delete_cols(headers.index(name) + 1)
    headers = [cell.value for cell in ws[1]]


async def async_main():
  logging.info("SC_Options_fromTasty.py  0.10-0.30 |delta|  next 8 expiries")
  tickers = load_tickers()
  src = "argv" if len(sys.argv) > 1 else tracklist_path
  logging.info("Loaded " + str(len(tickers)) + " tickers from " + src)
  if not tickers:
    logging.error("No tickers in Tracklist.csv Tickers column")
    return
  client_id, client_secret, refresh_token = load_creds()
  api = TastyRest(client_id, client_secret, refresh_token)
  today = dt.datetime.now(ZoneInfo("America/New_York")).date()
  metrics_by = api.market_metrics(tickers)
  ticker_metrics = build_ticker_metrics(tickers, metrics_by, api, today)
  dx_url, dx_token = api.quote_token()

  frames = {}
  for ticker in tickers:
    logging.info("=== " + ticker + " ===")
    try:
      df, spot = await pull_ticker(api, ticker, dx_url, dx_token)
      frames[ticker] = df
      logging.info(ticker + " rows=" + str(len(df)) + " spot=" + str(spot))
    except Exception as exc:
      logging.error(ticker + " failed: " + type(exc).__name__ + " " + str(exc))
      logging.debug(traceback.format_exc())
      frames[ticker] = pd.DataFrame()

  summary = build_summary(frames)
  out_path = _output_path()
  try:
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
      ticker_metrics.to_excel(writer, sheet_name="Ticker-metrics", index=False)
      _style_ticker_metrics(writer.sheets["Ticker-metrics"])
      if summary.empty:
        pd.DataFrame({"Message": ["No 0.10-0.30 delta contracts"]}).to_excel(
          writer, sheet_name="Summary", index=False
        )
        _style_sheet(writer.sheets["Summary"])
      else:
        summary = _with_group_blanks(summary, "Ticker")
        summary.to_excel(writer, sheet_name="Summary", index=False)
        _style_sheet(writer.sheets["Summary"], delta_as_pct=True)
      used = {"Ticker-metrics", "Summary", "Notes"}
      for ticker in tickers:
        name = sheet_name(ticker)
        base = name
        n = 2
        while name in used:
          name = (base[:28] + "_" + str(n))[:31]
          n += 1
        used.add(name)
        raw = frames.get(ticker)
        if raw is None or raw.empty:
          pd.DataFrame({"Message": [ticker + ": no 0.10-0.30 delta contracts"]}).to_excel(
            writer, sheet_name=name, index=False
          )
          _style_sheet(writer.sheets[name])
          continue
        otm = ticker_sheet_df(raw)
        otm.to_excel(writer, sheet_name=name, index=False)
        _style_sheet(
          writer.sheets[name],
          moneyness_as_pct=True,
          color_by_type=True,
          delta_as_pct=True,
        )
      notes_df().to_excel(writer, sheet_name="Notes", index=False)
      _style_notes(writer.sheets["Notes"])
  except PermissionError:
    logging.error("Cannot write " + out_path + " — close the file in Excel and re-run")
    return

  logging.info("Wrote " + out_path)
  for ticker in tickers:
    logging.info(format_ticker_got(ticker, frames.get(ticker)))


def main():
  asyncio.run(async_main())


if __name__ == "__main__":
  main()
