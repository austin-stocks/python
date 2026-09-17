# ##############################################################################
# Download SEC XBRL GAAP diluted EPS (quarterly) for each ticker in
# Tracklist.csv. For each ticker, writes a separate CSV.
#
# NOTE: Adjusted / non-GAAP EPS is NOT a standard XBRL concept and is not
# reliably available as structured SEC data. For adjusted EPS use the CNBC
# scraper output (epsAdjActualValue) - see SC_CNBC_Earnings_Quarterly.py.
#
# Ladder — each step only fills PeriodEnds still blank (merge, not replace):
#   1. companyconcept JSON  EarningsPerShareDiluted, then Basic
#      (HTTP 200 with an empty units dict counts as a miss, e.g. INCY)
#   2. companyfacts JSON  other tags for dates concept did not have
#      (BasicAndDiluted, continuing-ops, e.g. LFST / RLAY 2021 Q1-Q2)
#   3. 10-Q instance XBRL for leftover Q1-Q3 (forms 10-Q, 10-Q/A).
#      If JSON produced nothing this is the spine (e.g. FOUR). FPIs often
#      have no 10-Q; 6-K HTML in step 4 stands in. A 10-Q or Item 2.02
#      8-K / earnings 6-K newer than the last JSON quarter is treated as
#      missing (JSON lag; e.g. KNSA 2026 Q2).
#   4. 8-K / 6-K HTML earnings release (Exhibit 99.1), e.g. HNGE Q4'25
#      = 0.37; also INCY "GAAP diluted EPS", XNCR "net loss per share
#      (diluted)", FOUR image-letter hidden text / GAAP DILUTED EPS
#      recon row, GMED bullets. 6-K is the foreign-issuer current report
#      (8-K analog) and how FPIs furnish interims. If JSON+10-Q produced
#      nothing, walk 6-Ks and Item 2.02 8-Ks newest-first. Do not invent
#      lookback dates. 8-K HTML rules (keep generalizing, do not special-case
#      one ticker): GAAP diluted only; skip non-GAAP; "basic and diluted" is
#      diluted; three-months/quarter columns only (Years Ended / Year Ended /
#      Twelve Months Ended are FY, never Q4); do not overwrite a quarter
#      cell with FY for the same date; stitch Workiva '$' '(0.79' ')' cells;
#      one exhibit = current year only (drop YoY); exhibit may be named
#      *earningspressrel* not *ex99*; attach a number only if
#      the 8-K was filed 0-100 days after that quarter-end; 8-K reportDate
#      is often the press day — infer the last completed quarter from the
#      filing date. Known checks: KNSA Q4'22=0.06 not FY 2.60; Q4'20=-0.79
#      from 2021-02-23 8-K not FY-sum.
#   5. 10-K / 20-F instance XBRL (forms 10-K, 10-K/A, 20-F, 20-F/A)
#      for leftover quarters and the annual fact
#   6. 10-K / 20-F HTML "Quarterly Financial Data" table (e.g. DGII FY 2009)
#   7. compute Q4 as FY-(Q1+Q2+Q3) then FY-9mo — last resort only.
#      8-K almost always has Q4; skip compute on IPO / share-count break.
#
# Data source: SEC EDGAR data.sec.gov JSON APIs + EDGAR archives for instances
#   ticker->CIK map:  https://www.sec.gov/files/company_tickers.json
#   companyconcept:   https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}
#                       /us-gaap/{tag}.json
#   companyfacts:     https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json
#   submissions:      https://data.sec.gov/submissions/CIK{cik:010d}.json
#
# SEC Fair Access requires a User-Agent identifying the requester. Rate limit
# is 10 req/s; we sleep briefly between requests.
# ##############################################################################

import calendar
import csv
import io
import logging
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

# =============================================================================
# SETTINGS
# =============================================================================
USER_AGENT = "Sundeep Chadha sundeep.chadha@gmail.com"
REQUEST_SLEEP_SEC = 0.15
REQUEST_TIMEOUT_SEC = 60
XBRL_MAX_FILINGS = 30
XBRL_GAPFILL_MAX_FILINGS = 12
_8K_MAX_FILINGS = 32
_8K_FILED_AFTER_MAX_DAYS = 100
_filings_cache = {}
_8k_cache = {}
_submissions_data_cache = {}
_companyfacts_cache = {}

dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
tracklist_file = "Tracklist.csv"
tracklist_file_full_path = dir_path + user_dir + "\\" + tracklist_file

sec_out_dir = dir_path + "\\..\\SEC_Earnings"
log_dir = "\\..\\..\\..\\Automation_Not_in_Git\\" + "Logs"

os.makedirs(dir_path + log_dir, exist_ok=True)
# File gets DEBUG+; console (stdout) gets INFO+ only — same split as
# SC_YahooHistorical_Merge.py
logging.basicConfig(
  level=logging.DEBUG,
  format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
  datefmt="%m-%d %H:%M",
  filename=dir_path + log_dir + "\\" + "SC_SEC_EPS_Quarterly_debug.txt",
  filemode="w",
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter("%(name)-12s: %(levelname)-8s %(message)s")
console.setFormatter(formatter)
logging.getLogger("").addHandler(console)

logging.disable(sys.maxsize)
logging.disable(logging.NOTSET)

SESSION = requests.Session()
SESSION.headers.update({
  "User-Agent": USER_AGENT,
  "Accept-Encoding": "gzip, deflate",
  "Host": None,
})

# =============================================================================
# LOAD TRACKLIST
# =============================================================================
tracklist_df = pd.read_csv(tracklist_file_full_path)
ticker_list_unclean = tracklist_df["Tickers"].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != "nan"]

logging.info(f"Loaded {len(ticker_list)} tickers from {tracklist_file_full_path}")
logging.info(
  "Ladder (merge missing dates): companyconcept JSON -> companyfacts "
  "JSON (other tags) -> 10-Q instance XBRL -> 8-K / 6-K HTML -> "
  "10-K / 20-F instance XBRL -> 10-K / 20-F HTML -> "
  "FY-(Q1+Q2+Q3) / FY-9mo (last resort)."
)
logging.debug("Ticker list: " + str(ticker_list))

Path(sec_out_dir).mkdir(parents=True, exist_ok=True)


# Tag search order. companyconcept only uses the first two; companyfacts and
# 10-Q / 10-K / 20-F instance XBRL use the full list.
INSTANCE_XBRL_LADDER = "10-Q, 10-K and 20-F instance XBRL"
TEN_Q_XBRL_LADDER = "10-Q instance XBRL"
ANNUAL_XBRL_LADDER = "10-K / 20-F instance XBRL"
CURRENT_HTML_LADDER = "8-K / 6-K HTML"
ANNUAL_HTML_LADDER = "10-K / 20-F HTML"
FINANCIAL_FORMS = ("10-Q", "10-K", "10-Q/A", "10-K/A", "20-F", "20-F/A")
TEN_Q_FORMS = ("10-Q", "10-Q/A")
ANNUAL_XBRL_FORMS = ("10-K", "10-K/A", "20-F", "20-F/A")
CURRENT_REPORT_FORMS = ("8-K", "8-K/A", "6-K", "6-K/A")
EPS_TAG_PRIORITY = [
  ("EarningsPerShareDiluted", "Diluted"),
  ("EarningsPerShareBasic", "Basic"),
  ("EarningsPerShareBasicAndDiluted", "BasicAndDiluted"),
  ("IncomeLossFromContinuingOperationsPerDilutedShare", "ContinuingOpsDiluted"),
  ("IncomeLossFromContinuingOperationsPerBasicShare", "ContinuingOpsBasic"),
  ("IncomeLossFromContinuingOperationsPerBasicAndDilutedShare", "ContinuingOpsBasicAndDiluted"),
]
COMPANYCONCEPT_TAGS = EPS_TAG_PRIORITY[:2]
# companyfacts: Diluted spine first, then BasicAndDiluted, then the rest.
FACTS_TAG_PRIORITY = [
  EPS_TAG_PRIORITY[0],
  EPS_TAG_PRIORITY[2],
  EPS_TAG_PRIORITY[1],
] + EPS_TAG_PRIORITY[3:]


# =============================================================================
# TICKER -> CIK MAP (fetch once, cache in memory)
# =============================================================================
def load_ticker_cik_map():
  url = "https://www.sec.gov/files/company_tickers.json"
  logging.info(f"Fetching ticker->CIK map from {url}")
  resp = SESSION.get(url, timeout=REQUEST_TIMEOUT_SEC)
  resp.raise_for_status()
  raw = resp.json()
  mapping = {}
  for entry in raw.values():
    ticker = str(entry["ticker"]).upper()
    cik = int(entry["cik_str"])
    mapping[ticker] = cik
  logging.info(f"Loaded CIK for {len(mapping)} tickers")
  return mapping


def _http_get(url, ticker, what):
  logging.debug("[" + ticker + "] GET " + url + "  (" + what + ")")
  time.sleep(REQUEST_SLEEP_SEC)
  resp = SESSION.get(url, timeout=REQUEST_TIMEOUT_SEC)
  logging.debug(
    "[" + ticker + "] " + what + " HTTP " + str(resp.status_code)
    + " bytes=" + str(len(resp.content))
  )
  return resp


def _facts_shape(facts_json):
  """Short description of a companyconcept/companyfacts-tag payload."""
  if not facts_json:
    return "empty/None"
  units = facts_json.get("units", {})
  unit_bits = []
  for unit_key, entries in units.items():
    n = len(entries) if hasattr(entries, "__len__") else "?"
    unit_bits.append(str(unit_key) + "=" + str(n) + "(" + type(entries).__name__ + ")")
  return (
    "entity=" + str(facts_json.get("entityName"))
    + " tag=" + str(facts_json.get("tag"))
    + " units={" + ", ".join(unit_bits) + "}"
  )


def _usable_units(facts_json):
  """Return a units dict that contains at least one non-empty list, else None.

  INCY companyconcept returns HTTP 200 with units={'USD/shares': {}} — that
  is not usable.
  """
  if not facts_json:
    return None
  units = facts_json.get("units") or {}
  cleaned = {}
  for unit_key, entries in units.items():
    if isinstance(entries, list) and entries:
      cleaned[unit_key] = entries
  return cleaned or None


def _rows_from_facts(facts_json, ticker, concept_label, reset_globals=True):
  usable = _usable_units(facts_json)
  if not usable:
    logging.debug("[" + ticker + "] no usable unit lists: " + _facts_shape(facts_json))
    return []
  wrapped = dict(facts_json)
  wrapped["units"] = usable
  return extract_quarterly_rows(
    wrapped, ticker, concept_label, reset_globals=reset_globals
  )


# =============================================================================
# 1. COMPANYCONCEPT
# =============================================================================
def try_companyconcept(cik, ticker):
  global last_json_method
  last_json_method = "companyconcept"
  logging.debug("[" + ticker + "] method=companyconcept")
  for tag, label in COMPANYCONCEPT_TAGS:
    url = (
      f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}"
      f"/us-gaap/{tag}.json"
    )
    resp = _http_get(url, ticker, "companyconcept " + tag)
    if resp.status_code == 404:
      logging.debug("[" + ticker + "] companyconcept " + tag + " not tagged (404)")
      continue
    resp.raise_for_status()
    facts_json = resp.json()
    logging.debug("[" + ticker + "] companyconcept " + tag + " payload: " + _facts_shape(facts_json))
    rows = _rows_from_facts(facts_json, ticker, label)
    if rows:
      return rows, "companyconcept", tag, label
    logging.debug("[" + ticker + "] companyconcept " + tag + " had no quarterly rows")
  return None, None, None, None


# =============================================================================
# 2. COMPANYFACTS
# =============================================================================
def _load_companyfacts_gaap(cik, ticker):
  if cik in _companyfacts_cache:
    return _companyfacts_cache[cik]
  url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
  resp = _http_get(url, ticker, "companyfacts")
  if resp.status_code == 404:
    logging.debug("[" + ticker + "] companyfacts 404")
    _companyfacts_cache[cik] = None
    return None
  resp.raise_for_status()
  data = resp.json()
  gaap = (data.get("facts") or {}).get("us-gaap") or {}
  logging.debug(
    "[" + ticker + "] companyfacts entity=" + str(data.get("entityName"))
    + " us-gaap tags=" + str(len(gaap))
  )
  present = [tag for tag, _ in EPS_TAG_PRIORITY if tag in gaap]
  logging.debug(
    "[" + ticker + "] companyfacts EPS-like tags present: " + str(present)
  )
  _companyfacts_cache[cik] = gaap
  return gaap


def _rows_from_gaap_tag(gaap, ticker, tag, label, reset_globals=True):
  node = gaap.get(tag)
  if not node:
    return []
  facts_json = {
    "entityName": ticker,
    "tag": tag,
    "units": node.get("units") or {},
  }
  logging.debug(
    "[" + ticker + "] companyfacts " + tag + " payload: "
    + _facts_shape(facts_json)
  )
  return _rows_from_facts(
    facts_json, ticker, label, reset_globals=reset_globals
  )


def try_companyfacts(cik, ticker):
  global last_json_method
  last_json_method = "companyfacts"
  logging.debug("[" + ticker + "] method=companyfacts")
  gaap = _load_companyfacts_gaap(cik, ticker)
  if not gaap:
    return None, None, None, None
  for tag, label in FACTS_TAG_PRIORITY:
    rows = _rows_from_gaap_tag(gaap, ticker, tag, label, reset_globals=True)
    if rows:
      return rows, "companyfacts", tag, label
    logging.debug("[" + ticker + "] companyfacts " + tag + " had no quarterly rows")
  return None, None, None, None


def merge_facts_other_tags(cik, ticker, rows, used_tag):
  """Add ~90-day facts from companyfacts tags other than used_tag.

  Order: BasicAndDiluted, then Basic, then continuing-ops. Does not
  overwrite PeriodEnds already on the spine (usually Diluted).
  Returns (rows, added_by_tag) where added_by_tag is
  [(tag, label, [rows]), ...].
  """
  rows = list(rows) if rows else []
  gaap = _load_companyfacts_gaap(cik, ticker)
  if not gaap:
    return rows, []
  have = {r["PeriodEnd"] for r in rows if r.get("PeriodEnd")}
  added_by_tag = []
  for tag, label in FACTS_TAG_PRIORITY:
    if used_tag and tag == used_tag:
      continue
    extra = _rows_from_gaap_tag(
      gaap, ticker, tag, label, reset_globals=False
    )
    batch = []
    for r in extra:
      pe = r.get("PeriodEnd")
      if not pe or pe in have:
        continue
      if r.get("EPS_GAAP") is None:
        continue
      batch.append(r)
      have.add(pe)
    batch = _dedupe_by_period_end(batch)
    if not batch:
      continue
    batch.sort(key=lambda r: r["PeriodEnd"])
    bits = "; ".join(
      r["PeriodEnd"] + "=" + str(r["EPS_GAAP"]) for r in batch
    )
    _say(
      ticker,
      "Companyfacts " + tag + " filled " + str(len(batch))
      + " quarter(s): " + bits,
    )
    added_by_tag.append((tag, label, batch))
    rows.extend(batch)
  return rows, added_by_tag


# =============================================================================
# 3. 10-Q / 10-K / 20-F INSTANCE XBRL
# =============================================================================
def _local_name(tag):
  if tag is None:
    return ""
  if "}" in tag:
    return tag.rsplit("}", 1)[1]
  if ":" in tag:
    return tag.split(":")[-1]
  return tag


def _stock_class_rank(dims):
  text = " ".join(str(v) for v in dims.values()).lower().replace(" ", "")
  if "commonclassa" in text or "classamember" in text:
    return 0
  if not dims:
    return 1
  return 2


def _pick_stock_class(entries):
  """Prefer Class A (listed share); else undimensioned; else whatever is there."""
  if not entries:
    return entries
  ranks = [_stock_class_rank(e.get("_dims") or {}) for e in entries]
  if 0 in ranks:
    want = 0
    label = "ClassA"
  elif 1 in ranks:
    want = 1
    label = "entity"
  else:
    want = 2
    label = "other-class"
  picked = [e for e, r in zip(entries, ranks) if r == want]
  return picked, label


def _parse_contexts_et(root):
  contexts = {}
  for el in root.iter():
    if _local_name(el.tag) != "context":
      continue
    cid = el.get("id")
    if not cid:
      continue
    start = end = None
    dims = {}
    for child in el.iter():
      name = _local_name(child.tag)
      if name == "startDate" and child.text:
        start = child.text.strip()
      elif name == "endDate" and child.text:
        end = child.text.strip()
      elif name == "explicitMember" and child.text:
        axis = _local_name(child.get("dimension") or "")
        member = _local_name(child.text.strip())
        if axis:
          dims[axis] = member
    contexts[cid] = {"start": start, "end": end, "dims": dims}
  return contexts


def _parse_xbrl_et(xml_bytes):
  root = ET.fromstring(xml_bytes)
  contexts = _parse_contexts_et(root)
  wanted = {tag for tag, _ in EPS_TAG_PRIORITY}
  by_tag = {tag: [] for tag in wanted}
  for el in root.iter():
    tag = _local_name(el.tag)
    if tag not in wanted:
      continue
    if (el.get("nil") or "").lower() == "true":
      continue
    ctx = contexts.get(el.get("contextRef") or "")
    if not ctx or not ctx["start"] or not ctx["end"]:
      continue
    text = (el.text or "").strip()
    if not text:
      continue
    try:
      val = float(text)
    except ValueError:
      continue
    by_tag[tag].append({
      "start": ctx["start"],
      "end": ctx["end"],
      "val": val,
      "_dims": ctx["dims"],
    })
  return by_tag


_CONTEXT_RE = re.compile(r'<context\s+id="([^"]+)"\s*>(.*?)</context>', re.S | re.I)
_START_RE = re.compile(r"<startDate>([^<]+)</startDate>", re.I)
_END_RE = re.compile(r"<endDate>([^<]+)</endDate>", re.I)
_MEMBER_RE = re.compile(
  r'<[^>]*explicitMember[^>]*dimension="([^"]+)"[^>]*>([^<]+)</',
  re.I,
)
_FACT_RE = re.compile(
  r"<([A-Za-z0-9_-]+):(EarningsPerShareDiluted|EarningsPerShareBasic|"
  r"EarningsPerShareBasicAndDiluted|"
  r"IncomeLossFromContinuingOperationsPerDilutedShare|"
  r"IncomeLossFromContinuingOperationsPerBasicShare|"
  r"IncomeLossFromContinuingOperationsPerBasicAndDilutedShare)"
  r"\b([^>]*)>([^<]*)</",
  re.I,
)


def _parse_xbrl_regex(xml_text):
  contexts = {}
  for cid, blob in _CONTEXT_RE.findall(xml_text):
    sm = _START_RE.search(blob)
    em = _END_RE.search(blob)
    dims = {}
    for axis, member in _MEMBER_RE.findall(blob):
      dims[_local_name(axis)] = _local_name(member.strip())
    contexts[cid] = {
      "start": sm.group(1).strip() if sm else None,
      "end": em.group(1).strip() if em else None,
      "dims": dims,
    }

  wanted = {tag for tag, _ in EPS_TAG_PRIORITY}
  by_tag = {tag: [] for tag in wanted}
  for _prefix, tag, attrs, text in _FACT_RE.findall(xml_text):
    if tag not in wanted:
      continue
    if re.search(r'\bnil="true"', attrs, re.I):
      continue
    ctx_m = re.search(r'contextRef="([^"]+)"', attrs)
    if not ctx_m:
      continue
    ctx = contexts.get(ctx_m.group(1))
    if not ctx or not ctx["start"] or not ctx["end"]:
      continue
    text = (text or "").strip()
    if not text:
      continue
    try:
      val = float(text)
    except ValueError:
      continue
    by_tag[tag].append({
      "start": ctx["start"],
      "end": ctx["end"],
      "val": val,
      "_dims": ctx["dims"],
    })
  return by_tag


def _parse_instance_eps(xml_bytes, ticker):
  try:
    by_tag = _parse_xbrl_et(xml_bytes)
    n = sum(len(v) for v in by_tag.values())
    logging.debug("[" + ticker + "] XBRL ElementTree facts=" + str(n))
    if n:
      return by_tag
  except Exception:
    logging.debug("[" + ticker + "] XBRL ElementTree parse failed", exc_info=True)
  try:
    text = xml_bytes.decode("utf-8", errors="replace")
  except Exception:
    text = str(xml_bytes)
  by_tag = _parse_xbrl_regex(text)
  n = sum(len(v) for v in by_tag.values())
  logging.debug("[" + ticker + "] XBRL regex facts=" + str(n))
  return by_tag


def _instance_xml_name(file_names):
  names = [n for n in file_names if n]
  for n in names:
    if n.lower().endswith("_htm.xml"):
      return n
  for n in names:
    nl = n.lower()
    if not nl.endswith(".xml"):
      continue
    if any(x in nl for x in ("_cal", "_def", "_lab", "_pre", "xsl", "filingsummary", "metalinks")):
      continue
    return n
  return None


def _is_annual_report_form(form):
  f = str(form or "")
  return f.startswith("10-K") or f.startswith("20-F")


def _filings_from_recent(recent, allowed_forms=None):
  if allowed_forms is None:
    allowed_forms = FINANCIAL_FORMS
  forms = recent.get("form") or []
  accs = recent.get("accessionNumber") or []
  dates = recent.get("filingDate") or []
  reports = recent.get("reportDate") or []
  prim = recent.get("primaryDocument") or []
  items = recent.get("items") or []
  kept = []
  for i, form in enumerate(forms):
    if form not in allowed_forms:
      continue
    kept.append({
      "form": form,
      "filed": dates[i] if i < len(dates) else "",
      "report": reports[i] if i < len(reports) else "",
      "accn": accs[i] if i < len(accs) else "",
      "primary": prim[i] if i < len(prim) else "",
      "items": items[i] if i < len(items) else "",
    })
  kept.sort(key=lambda r: r["filed"], reverse=True)
  return kept


def _form_tally(filings):
  """Stdout bit like '10-K x4, 10-K/A x2, 10-Q x6, 20-F x1'."""
  counts = {}
  for f in filings:
    form = str(f.get("form") or "?")
    counts[form] = counts.get(form, 0) + 1
  order = ("10-K", "10-K/A", "10-Q", "10-Q/A", "20-F", "20-F/A")
  bits = []
  for form in order:
    n = counts.pop(form, 0)
    if n:
      bits.append(form + " x" + str(n))
  for form in sorted(counts):
    bits.append(form + " x" + str(counts[form]))
  return ", ".join(bits) if bits else "none"


def _recent_financial_filings(sub_json):
  recent = (sub_json.get("filings") or {}).get("recent") or {}
  return _filings_from_recent(recent)[:XBRL_MAX_FILINGS]


def _submissions_data(cik, ticker):
  if cik in _submissions_data_cache:
    return _submissions_data_cache[cik]
  url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
  resp = _http_get(url, ticker, "submissions")
  if resp.status_code == 404:
    logging.debug("[" + ticker + "] submissions 404")
    _submissions_data_cache[cik] = None
    return None
  resp.raise_for_status()
  data = resp.json()
  _submissions_data_cache[cik] = data
  return data


def _load_financial_filings(cik, ticker):
  cached = _filings_cache.get(cik)
  if cached is not None:
    return cached
  data = _submissions_data(cik, ticker)
  if not data:
    _filings_cache[cik] = []
    return []
  filings = _filings_from_recent((data.get("filings") or {}).get("recent") or {})
  for extra in (data.get("filings") or {}).get("files") or []:
    name = extra.get("name")
    if not name:
      continue
    extra_url = "https://data.sec.gov/submissions/" + name
    extra_resp = _http_get(extra_url, ticker, "submissions-extra " + name)
    if extra_resp.status_code != 200:
      continue
    extra_json = extra_resp.json()
    if "form" in extra_json:
      rec = extra_json
    else:
      rec = (extra_json.get("filings") or {}).get("recent") or extra_json
    if isinstance(rec, dict) and rec.get("form"):
      filings.extend(_filings_from_recent(rec))
  seen = set()
  uniq = []
  for f in filings:
    accn = f.get("accn")
    if not accn or accn in seen:
      continue
    seen.add(accn)
    uniq.append(f)
  uniq.sort(key=lambda r: r["filed"], reverse=True)
  logging.debug("[" + ticker + "] submissions 10-Q/K/20-F total=" + str(len(uniq)))
  _filings_cache[cik] = uniq
  return uniq


def _add_months_clamped(d, months):
  m0 = d.month - 1 + months
  y = d.year + m0 // 12
  m = m0 % 12 + 1
  day = min(d.day, calendar.monthrange(y, m)[1])
  return date(y, m, day)


def _fye_from_latest_annual_report(cik, ticker):
  """reportDate of the newest 10-K / 20-F. None if absent."""
  filings = _load_financial_filings(cik, ticker)
  annuals = [f for f in filings if _is_annual_report_form(f.get("form"))]
  annuals.sort(key=lambda f: f.get("filed") or "", reverse=True)
  for f in annuals:
    rd = (f.get("report") or "")[:10]
    if not rd:
      continue
    try:
      d = parse_iso(rd)
    except Exception:
      continue
    if d is not None:
      _say(
        ticker,
        "Fiscal year-end from latest "
        + str(f.get("form")) + " reportDate " + d.isoformat()
        + " (filed " + str(f.get("filed") or "") + ")",
      )
      return d
  return None


def _require_fye(cik, ticker):
  global last_fye
  fye = _fye_from_latest_annual_report(cik, ticker)
  if fye is None:
    logging.error(
      ticker
      + "  No fiscal year-end: latest 10-K/20-F has no reportDate. Stopping."
    )
    sys.exit(1)
  last_fye = fye
  return fye


def _fye_on_or_after(end_d):
  md = (last_fye.month, last_fye.day) if last_fye else (12, 31)
  day = min(md[1], calendar.monthrange(end_d.year, md[0])[1])
  fy = date(end_d.year, md[0], day)
  if end_d <= fy:
    return fy
  day = min(md[1], calendar.monthrange(end_d.year + 1, md[0])[1])
  return date(end_d.year + 1, md[0], day)


def _fiscal_q_ends_for_fy(fy_end):
  return [
    _add_months_clamped(fy_end, -9),
    _add_months_clamped(fy_end, -6),
    _add_months_clamped(fy_end, -3),
    fy_end,
  ]


def _fiscal_year_and_quarter(end_d):
  fy_end = _fye_on_or_after(end_d)
  qs = _fiscal_q_ends_for_fy(fy_end)
  best_i, best_dist = 4, 10 ** 6
  for i, qe in enumerate(qs, start=1):
    dist = abs((end_d - qe).days)
    if dist < best_dist:
      best_dist, best_i = dist, i
  return fy_end.year, best_i


def _next_fiscal_quarter_end(d):
  fy_end = _fye_on_or_after(d)
  for qe in _fiscal_q_ends_for_fy(fy_end):
    if qe > d:
      return qe
  return _add_months_clamped(fy_end, 3)


def _snap_to_fiscal_q_end(d, max_days=15):
  fy_end = _fye_on_or_after(d)
  prev = _add_months_clamped(fy_end, -12)
  cands = _fiscal_q_ends_for_fy(prev) + _fiscal_q_ends_for_fy(fy_end)
  nxt = _add_months_clamped(fy_end, 12)
  cands.extend(_fiscal_q_ends_for_fy(nxt))
  best, dist = None, 10 ** 6
  for qe in cands:
    dd = abs((d - qe).days)
    if dd < dist:
      best, dist = qe, dd
  if best is not None and dist <= max_days:
    return best
  return None


def _append_submission_extras(data, ticker, filings, allowed_forms):
  """Older EDGAR submission chunks (beyond filings.recent)."""
  for extra in (data.get("filings") or {}).get("files") or []:
    name = extra.get("name")
    if not name:
      continue
    extra_url = "https://data.sec.gov/submissions/" + name
    extra_resp = _http_get(extra_url, ticker, "submissions-extra " + name)
    if extra_resp.status_code != 200:
      continue
    extra_json = extra_resp.json()
    if "form" in extra_json:
      rec = extra_json
    else:
      rec = (extra_json.get("filings") or {}).get("recent") or extra_json
    if isinstance(rec, dict) and rec.get("form"):
      filings.extend(_filings_from_recent(rec, allowed_forms=allowed_forms))
  return filings


def _load_8k_filings(cik, ticker):
  cached = _8k_cache.get(cik)
  if cached is not None:
    return cached
  data = _submissions_data(cik, ticker)
  if not data:
    _8k_cache[cik] = []
    return []
  filings = _filings_from_recent(
    (data.get("filings") or {}).get("recent") or {},
    allowed_forms=CURRENT_REPORT_FORMS,
  )
  filings = _append_submission_extras(
    data, ticker, filings, CURRENT_REPORT_FORMS
  )
  seen = set()
  uniq = []
  for f in filings:
    accn = f.get("accn")
    if not accn or accn in seen:
      continue
    seen.add(accn)
    uniq.append(f)
  uniq.sort(key=lambda r: r["filed"], reverse=True)
  logging.debug("[" + ticker + "] submissions 8-K/6-K total=" + str(len(uniq)))
  _8k_cache[cik] = uniq
  return uniq


def _current_report_earnings_score(f, end_d):
  """Prefer 8-K Item 2.02; for 6-K, prefer a report date / filename match.

  6-K has no Item 2.02. FPIs put the quarter in the primary name
  (bsp-20260630x6k.htm) or reportDate. Without that, the two soonest
  6-Ks after quarter-end can be an acquisition 6-K, not earnings.
  """
  if "2.02" in str(f.get("items") or ""):
    return 1
  if not str(f.get("form") or "").startswith("6-K"):
    return 0
  blob = (
    str(f.get("primary") or "") + str(f.get("report") or "")
  ).lower().replace("-", "").replace("_", "")
  if end_d.strftime("%Y%m%d") in blob or end_d.strftime("%Y%m") in blob:
    return 1
  rd = (f.get("report") or "")[:10]
  if rd:
    try:
      if abs((parse_iso(rd) - end_d).days) <= 10:
        return 1
    except Exception:
      pass
  return 0


def _select_open_ended_current_reports(filings):
  """All 6-Ks and Item 2.02 8-Ks, newest first. No invented dates, no 32 cap.

  Other 8-K items are skipped (not earnings). Walk the whole list so we
  keep going back as long as filings can yield EPS.
  """
  selected = []
  seen = set()
  for f in filings:
    accn = f.get("accn")
    if not accn or accn in seen:
      continue
    form = str(f.get("form") or "")
    is_6k = form.startswith("6-K")
    is_earnings_8k = "2.02" in str(f.get("items") or "")
    if not (is_6k or is_earnings_8k):
      continue
    seen.add(accn)
    selected.append(f)
  selected.sort(key=lambda r: r.get("filed") or "", reverse=True)
  return selected


def _select_8k_for_ends(filings, missing_ends):
  """For each missing quarter-end, keep 8-K/6-Ks filed 0-100 days later.

  Prefer Item 2.02 (8-K earnings) or a 6-K report-date/filename match,
  then the soonest filing after the period end so a long missing list
  cannot push the relevant earnings filing past _8K_MAX_FILINGS.
  Keep up to two 8-Ks per end; up to eight 6-Ks (no 2.02 to rank on).
  """
  selected = []
  seen = set()
  for pe in missing_ends:
    try:
      end_d = parse_iso(pe)
    except Exception:
      continue
    cands = []
    n_keep = 2
    for f in filings:
      accn = f.get("accn")
      if not accn:
        continue
      fd = (f.get("filed") or "")[:10]
      if not fd:
        continue
      try:
        filed_d = parse_iso(fd)
      except Exception:
        continue
      delta = (filed_d - end_d).days
      if 0 <= delta <= _8K_FILED_AFTER_MAX_DAYS:
        if str(f.get("form") or "").startswith("6-K"):
          n_keep = 8
        earnings = _current_report_earnings_score(f, end_d)
        cands.append((earnings, -delta, f))
    cands.sort(key=lambda x: (x[0], x[1]), reverse=True)
    for _, _, f in cands[:n_keep]:
      accn = f.get("accn")
      if accn in seen:
        continue
      seen.add(accn)
      selected.append(f)
  # Newest first so a long list of old holes cannot drop the latest
  # earnings 8-K when we cap at _8K_MAX_FILINGS (INCY 2011 holes used to
  # push the 2026-02-10 Q4 exhibit off the list).
  selected.sort(key=lambda r: r.get("filed") or "", reverse=True)
  return selected[:_8K_MAX_FILINGS]


def _exhibit_99_name(names):
  """Pick the earnings exhibit HTML.

  Usually Exhibit 99.1 (incy-q42025xexx991.htm). Some issuers use a press
  release name instead (navnq4fy26earningspressrel.htm) with no '99'.
  """
  htmls = [n for n in names if n and n.lower().endswith((".htm", ".html"))]
  skip = ("index", "r1.htm", "show.js", "report.css")
  htmls = [
    n for n in htmls
    if not any(s in n.lower() for s in skip)
  ]
  compact_hit = re.compile(r"x?exx?991|exhibit991|ex99d1")
  for n in htmls:
    nl = n.lower().replace("_", "").replace("-", "").replace(".", "")
    if compact_hit.search(nl):
      return n
  for n in htmls:
    nl = n.lower()
    if "99.1" in nl or "99_1" in nl or "ex99" in nl:
      return n
  for n in htmls:
    nl = n.lower().replace("_", "").replace("-", "")
    if "earnings" in nl or "pressrel" in nl or "pressrelease" in nl:
      return n
  return None


def _select_gapfill_filings(filings, missing_ends, allowed_forms=None):
  if allowed_forms:
    filings = [f for f in filings if f.get("form") in allowed_forms]
  windows = [_fiscal_window(pe) for pe in missing_ends]
  selected = []
  seen = set()
  for f in filings:
    rd = (f.get("report") or "")[:10]
    if not rd:
      continue
    try:
      rd_d = parse_iso(rd)
    except Exception:
      continue
    form = f.get("form") or ""
    keep = False
    for fy_start, fy_end in windows:
      if fy_start <= rd_d <= fy_end:
        keep = True
        break
      if _is_annual_report_form(form):
        delta = (rd_d - fy_end).days
        # same 10-K/20-F, later annual in the same FY (~90 days after Q3),
        # plus next 1-2 years (prior-year comparatives)
        if abs(delta) <= 15 or 80 <= delta <= 800:
          keep = True
          break
    if not keep:
      continue
    accn = f.get("accn")
    if not accn or accn in seen:
      continue
    seen.add(accn)
    selected.append(f)
  selected.sort(key=lambda r: r["filed"], reverse=True)
  return selected[:XBRL_GAPFILL_MAX_FILINGS]


def _eps_entries_from_filings(cik, ticker, filings):
  by_tag = {tag: [] for tag, _ in EPS_TAG_PRIORITY}
  cik_nolead = str(int(cik))
  parsed_ok = 0
  no_xml = 0
  for filing in filings:
    accn = filing["accn"]
    if not accn:
      continue
    accn_nodash = accn.replace("-", "")
    index_url = (
      f"https://www.sec.gov/Archives/edgar/data/{cik_nolead}/{accn_nodash}/index.json"
    )
    try:
      idx_resp = _http_get(index_url, ticker, "index " + accn)
      if idx_resp.status_code != 200:
        continue
      items = (idx_resp.json().get("directory") or {}).get("item") or []
      names = [it.get("name") for it in items]
      xml_name = _instance_xml_name(names)
      if not xml_name:
        no_xml += 1
        logging.debug(
          "[" + ticker + "] no instance XML in " + accn
          + " report=" + str(filing.get("report"))
          + " form=" + str(filing.get("form"))
        )
        continue
      xml_url = (
        f"https://www.sec.gov/Archives/edgar/data/{cik_nolead}/{accn_nodash}/{xml_name}"
      )
      xml_resp = _http_get(xml_url, ticker, "instance " + xml_name)
      if xml_resp.status_code != 200:
        continue
      facts = _parse_instance_eps(xml_resp.content, ticker)
    except Exception:
      logging.debug("[" + ticker + "] failed filing " + accn, exc_info=True)
      continue
    parsed_ok += 1
    for tag, entries in facts.items():
      for e in entries:
        e["form"] = filing["form"]
        e["filed"] = filing["filed"]
        e["accn"] = accn
        by_tag[tag].append(e)
  logging.debug(
    "[" + ticker + "] parsed " + str(parsed_ok) + " 10-Q/K/20-F instances"
    + " no_xml=" + str(no_xml)
  )
  return by_tag, parsed_ok, no_xml


def try_xbrl_filings(cik, ticker, allowed_forms=None):
  global last_json_method
  allowed_forms = allowed_forms or FINANCIAL_FORMS
  last_json_method = INSTANCE_XBRL_LADDER
  logging.debug("[" + ticker + "] method=xbrl-10q forms=" + str(allowed_forms))
  filings = _load_financial_filings(cik, ticker)
  filings = [f for f in filings if f.get("form") in allowed_forms]
  filings = filings[:XBRL_MAX_FILINGS]
  logging.debug(
    "[" + ticker + "] submissions forms used=" + str(len(filings))
  )
  if not filings:
    return None, None, None, None

  by_tag, parsed_ok, _no_xml = _eps_entries_from_filings(cik, ticker, filings)
  logging.debug(
    "[" + ticker + "] parsed " + str(parsed_ok) + " instances"
  )

  have = set()
  all_rows = []
  method = None
  tag0 = None
  label0 = None
  reset = True
  for tag, label in EPS_TAG_PRIORITY:
    entries = by_tag.get(tag) or []
    if not entries:
      logging.debug("[" + ticker + "] xbrl-10q missing tag " + tag)
      continue
    picked, class_label = _pick_stock_class(entries)
    logging.debug(
      "[" + ticker + "] xbrl-10q " + tag
      + " raw=" + str(len(entries))
      + " after class-pick(" + class_label + ")=" + str(len(picked))
    )
    for e in picked:
      e.pop("_dims", None)
    facts_json = {
      "entityName": ticker,
      "tag": tag,
      "units": {"USD/shares": picked},
    }
    rows = _rows_from_facts(
      facts_json, ticker, label, reset_globals=reset
    )
    reset = False
    if not rows:
      logging.debug("[" + ticker + "] xbrl-10q " + tag + " had no quarterly rows")
      continue
    if method is None:
      method = "xbrl-10q/" + class_label
      tag0, label0 = tag, label
    for r in rows:
      pe = r.get("PeriodEnd")
      if pe and pe not in have:
        all_rows.append(r)
        have.add(pe)
  if all_rows:
    return all_rows, method, tag0, label0
  return None, None, None, None


def resolve_eps(cik, ticker):
  """JSON spine then filings. Each step fills PeriodEnds still blank.

  companyconcept -> companyfacts other tags -> 10-Q XML -> 8-K/6-K HTML
  -> 10-K/20-F XML -> 10-K HTML -> FY-(Q1+Q2+Q3) last.
  """
  global last_missing_after_json, last_newer_filing_ends, last_fye
  last_ladder.clear()
  last_annual_rows.clear()
  last_ytd_rows.clear()
  last_q4_cannot_ends.clear()
  last_q4_cannot_msgs.clear()
  last_q4_computes.clear()
  last_missing_after_json = []
  last_newer_filing_ends = []
  attempts = []
  _require_fye(cik, ticker)

  _say(ticker, "Trying companyconcept JSON")
  rows, method, tag, label = try_companyconcept(cik, ticker)
  attempts.append("companyconcept")
  rows = rows or []
  if rows:
    _ladder_step(
      "JSON", "companyconcept JSON", "hit", _json_span_bit(tag, rows)
    )
    _log_json_success(ticker, method, tag, rows)
  else:
    _say(ticker, "Companyconcept JSON had no quarterly EPS")
    _ladder_step(
      "JSON", "companyconcept JSON", "miss", "no quarterly EPS"
    )

  _say(ticker, "Trying companyfacts JSON")
  attempts.append("companyfacts")
  if not rows:
    f_rows, f_method, f_tag, f_label = try_companyfacts(cik, ticker)
    if f_rows:
      rows, method, tag, label = f_rows, f_method, f_tag, f_label
      _log_json_success(ticker, method, tag, list(f_rows))
      rows, added_by = merge_facts_other_tags(cik, ticker, rows, tag)
      detail = _json_span_bit(tag, f_rows)
      extra = _other_tags_recap(added_by)
      if extra:
        detail += "; " + extra
      _ladder_step("JSON", "companyfacts JSON", "hit", detail)
    else:
      _say(ticker, "Companyfacts JSON had no quarterly EPS")
      _ladder_step(
        "JSON", "companyfacts JSON", "miss", "no quarterly EPS"
      )
  else:
    rows, added_by = merge_facts_other_tags(cik, ticker, rows, tag)
    extra = _other_tags_recap(added_by)
    if extra:
      method = _append_method(method, "companyfacts")
      n_other = sum(len(rs) for _t, _l, rs in added_by)
      _ladder_step(
        "JSON", "companyfacts JSON (other tags)",
        _filled_status(n_other), extra,
      )
    else:
      missing = _still_missing_quarters(rows)
      _ladder_step(
        "JSON", "companyfacts JSON (other tags)", "no fill",
        ", ".join(missing) if missing else "no extra dates",
      )

  last_missing_after_json = _still_missing_quarters(rows) if rows else []
  _log_missing_after_json(ticker)
  return _finalize_rows(cik, ticker, rows, method, tag, label, attempts)


# =============================================================================
# FILTER + DEDUPE QUARTERLY FACTS
# =============================================================================
def parse_iso(s):
  return date.fromisoformat(s)


def duration_days(start, end):
  return (parse_iso(end) - parse_iso(start)).days + 1


def is_quarterly_duration(days):
  return 80 <= days <= 100


def is_annual_duration(days):
  return 350 <= days <= 380


def is_nine_month_duration(days):
  return 250 <= days <= 280


def _fiscal_window(fy_end_iso):
  fy_end = parse_iso(fy_end_iso)
  try:
    prev = date(fy_end.year - 1, fy_end.month, fy_end.day)
  except ValueError:
    prev = date(fy_end.year - 1, 2, 28)
  return prev + timedelta(days=1), fy_end


def _interior_missing_quarter_ends(rows):
  """Quarter-ends that are skipped between the first and last row."""
  ends = sorted({parse_iso(r["PeriodEnd"]) for r in rows if r.get("PeriodEnd")})
  if len(ends) < 2:
    return []
  have = list(ends)

  def covered(expected):
    for e in have:
      if abs((e - expected).days) <= 10:
        return True
    return False

  missing = []
  cur = _next_fiscal_quarter_end(ends[0])
  last = ends[-1]
  while cur < last - timedelta(days=15):
    if not covered(cur):
      missing.append(cur.isoformat())
    cur = _next_fiscal_quarter_end(cur)
  return missing


def _quarter_start(end_d):
  return _quarter_start_for_end(end_d)


def _placeholder_eps_row(ticker, pe_iso):
  """Keep the quarter on the CSV timeline with EPS_GAAP (col C) blank."""
  end_d = parse_iso(pe_iso)
  return {
    "Ticker": ticker,
    "Year": _fiscal_year_and_quarter(end_d)[0],
    "Quarter": _fiscal_year_and_quarter(end_d)[1],
    "PeriodStart": _quarter_start(end_d).isoformat(),
    "PeriodEnd": pe_iso,
    "EPS_GAAP": None,
    "EPS_Concept": "",
    "Source": "",
    "Form": "",
    "Filed": "",
    "AccessionNumber": "",
    "Unit": "",
  }


def insert_blank_missing_quarters(rows, ticker):
  """Insert a row for every still-missing quarter-end; leave EPS_GAAP empty."""
  missing = _still_missing_quarters(rows)
  if not missing:
    return rows
  have = {r["PeriodEnd"] for r in rows if r.get("PeriodEnd")}
  extra = [
    _placeholder_eps_row(ticker, pe) for pe in missing if pe not in have
  ]
  if not extra:
    return rows
  out = list(rows) + extra
  out.sort(key=lambda r: r["PeriodEnd"], reverse=True)
  _say(
    ticker,
    "Blank EPS_GAAP for missing quarter(s): " + ", ".join(missing),
  )
  return out


def _untagged_fy_q4_ends(rows):
  """FY period-ends that have an annual EPS fact but no 3-month Q4 row."""
  have = {r["PeriodEnd"] for r in rows if r.get("PeriodEnd")}
  out = []
  for fy in last_annual_rows:
    pe = fy.get("PeriodEnd")
    if pe and fy.get("EPS_GAAP") is not None and pe not in have:
      out.append(pe)
  return out


def _still_missing_quarters(rows):
  """Untagged Q4s, FY-compute skips, interior holes, newer 10-Qs."""
  have_eps = {
    r["PeriodEnd"] for r in rows
    if r.get("PeriodEnd") and r.get("EPS_GAAP") is not None
  }
  missing = []
  seen = set()
  for pe in (
    list(last_q4_cannot_ends)
    + _untagged_fy_q4_ends(rows)
    + _interior_missing_quarter_ends(rows)
    + list(last_newer_filing_ends)
  ):
    if pe in seen or pe in have_eps:
      continue
    seen.add(pe)
    missing.append(pe)
  missing.sort()
  return missing


def _calendar_quarter_end(d):
  snapped = _snap_to_fiscal_q_end(d, max_days=20)
  return snapped if snapped is not None else d


def _most_recent_completed_quarter_end(d):
  """Latest fiscal quarter-end on or before d (uses issuer FYE)."""
  fy_end = _fye_on_or_after(d)
  prev = _add_months_clamped(fy_end, -12)
  qs = _fiscal_q_ends_for_fy(prev) + _fiscal_q_ends_for_fy(fy_end)
  ok = [qe for qe in qs if qe <= d]
  return max(ok) if ok else None


def _latest_tagged_end(rows):
  ends = []
  for r in rows:
    pe = r.get("PeriodEnd")
    if not pe:
      continue
    try:
      ends.append(parse_iso(pe))
    except Exception:
      continue
  return max(ends) if ends else None


def _newer_10q_report_ends(cik, ticker, rows):
  """10-Q report dates after the latest tagged quarter (JSON lag)."""
  latest = _latest_tagged_end(rows)
  if latest is None:
    return []
  today = date.today()
  have = {latest.isoformat()}
  for r in rows:
    if r.get("PeriodEnd"):
      have.add(r["PeriodEnd"])
  found = []
  seen = set()
  for f in _load_financial_filings(cik, ticker):
    if (f.get("form") or "") not in TEN_Q_FORMS:
      continue
    rd = (f.get("report") or "")[:10]
    try:
      rd_d = parse_iso(rd)
    except Exception:
      continue
    if rd_d is None or rd_d <= latest or rd_d > today:
      continue
    q_end = _snap_to_fiscal_q_end(rd_d, max_days=15)
    if q_end is None:
      continue
    pe = q_end.isoformat()
    if pe in have or pe in seen:
      continue
    seen.add(pe)
    found.append(pe)
  found.sort()
  return found


def _newer_8k_report_ends(cik, ticker, rows):
  """Item 2.02 8-K / earnings 6-K after the latest tagged quarter.

  8-K reportDate is often the event day (28 Jul), not the quarter-end.
  Infer the most recent completed quarter on or before the filing date.
  6-Ks need a report-date or filename quarter match.
  """
  latest = _latest_tagged_end(rows)
  if latest is None:
    return []
  today = date.today()
  have = {r["PeriodEnd"] for r in rows if r.get("PeriodEnd")}
  found = []
  seen = set()
  for f in _load_8k_filings(cik, ticker):
    form = str(f.get("form") or "")
    is_6k = form.startswith("6-K")
    is_earnings_8k = "2.02" in str(f.get("items") or "")
    if not (is_6k or is_earnings_8k):
      continue
    fd = (f.get("filed") or "")[:10]
    try:
      filed_d = parse_iso(fd)
    except Exception:
      continue
    if filed_d is None or filed_d <= latest or filed_d > today:
      continue
    pe_d = None
    rd = (f.get("report") or "")[:10]
    if rd:
      try:
        rd_d = parse_iso(rd)
        q_end = _snap_to_fiscal_q_end(rd_d, max_days=15)
        if q_end is not None and q_end > latest:
          pe_d = q_end
      except Exception:
        pe_d = None
    if pe_d is None and is_earnings_8k:
      cand = _most_recent_completed_quarter_end(filed_d)
      if cand is not None and cand > latest and cand <= filed_d:
        pe_d = cand
    if pe_d is None:
      continue
    if is_6k and _current_report_earnings_score(f, pe_d) == 0:
      continue
    if pe_d <= latest or pe_d > today:
      continue
    pe = pe_d.isoformat()
    if pe in have or pe in seen:
      continue
    seen.add(pe)
    found.append(pe)
  found.sort()
  return found


def _sort_key(r):
  """Prefer earliest-filed; among ties, prefer non-amendment forms."""
  form = r["Form"] or ""
  is_amendment = form.endswith("/A")
  return (r["_filed_dt"] or date.max, 1 if is_amendment else 0)


def _make_row(ticker, unit_key, e, source, concept_label):
  end_dt = parse_iso(e["end"])
  fy_year, qn = _fiscal_year_and_quarter(end_dt)
  return {
    "Ticker": ticker,
    "Year": fy_year,
    "Quarter": qn,
    "PeriodStart": e["start"],
    "PeriodEnd": e["end"],
    "EPS_GAAP": e.get("val"),
    "EPS_Concept": concept_label,
    "Source": source,
    "Form": e.get("form"),
    "Filed": e.get("filed"),
    "AccessionNumber": e.get("accn"),
    "Unit": unit_key,
    "_filed_dt": parse_iso(e["filed"]) if e.get("filed") else None,
  }


def _dedupe_by_period_end(rows):
  grouped = {}
  for r in rows:
    key = r["PeriodEnd"]
    existing = grouped.get(key)
    if existing is None or _sort_key(r) < _sort_key(existing):
      grouped[key] = r
  return list(grouped.values())


# Period-ends of FYs we could not compute Q4 for, from the last extract
# that actually returned quarterly rows. Main prints this on the OK line.
last_q4_cannot_ends = []
last_q4_cannot_msgs = []
last_annual_rows = []
last_ytd_rows = []
last_q4_computes = []
last_json_method = ""
last_ladder = []
last_missing_after_json = []
last_newer_filing_ends = []
last_fye = None


def _say(ticker, msg):
  """Ticker-prefixed INFO line; first letter of the sentence capitalized."""
  s = str(msg).strip()
  if s:
    s = s[0].upper() + s[1:]
  logging.info(str(ticker) + "  " + s)


def _warn(ticker, msg):
  s = str(msg).strip()
  if s:
    s = s[0].upper() + s[1:]
  logging.warning(str(ticker) + "  " + s)


def _missing_after_line(after, missing):
  n = len(missing or [])
  if n:
    return (
      "Missing 3-month quarters after " + after
      + " (#" + str(n) + "): " + ", ".join(missing)
    )
  return "Missing 3-month quarters after " + after + " (#0): none"


def _ladder_step(group, name, status, detail=""):
  last_ladder.append((group, name, status, detail))


def _filled_status(n):
  return "filled (#" + str(int(n)) + ")"


def _n_filled_from_note(note):
  if not note:
    return 0
  main = str(note).split(" [opened")[0]
  main = main.split("; still unfilled")[0]
  main = main.split("; then computed")[0]
  return main.count("=")


def _ladder_hit_detail(rows):
  tagged = [
    r for r in rows
    if str(r.get("Source") or "").startswith("XBRL")
  ]
  if not tagged:
    tagged = list(rows)
  ends = [r["PeriodEnd"] for r in tagged if r.get("PeriodEnd")]
  if not ends:
    return str(len(tagged)) + " quarter(s)"
  return str(len(tagged)) + " quarters " + min(ends) + ".." + max(ends)


def _ladder_source_bits(rows, source):
  rs = [r for r in rows if r.get("Source") == source]
  rs.sort(key=lambda r: r.get("PeriodEnd") or "")
  return "; ".join(
    r["PeriodEnd"] + "=" + str(r["EPS_GAAP"]) for r in rs
  )


def _ladder_source_bits_any(rows, sources):
  parts = [_ladder_source_bits(rows, s) for s in sources]
  return "; ".join(p for p in parts if p)


def _group_header(group):
  if group == "JSON":
    return "JSON"
  if not group:
    return group
  return group[0].upper() + group[1:]


def _other_tags_recap(added_by_tag):
  parts = []
  for tag, _label, rs in added_by_tag:
    bits = "; ".join(
      r["PeriodEnd"] + "=" + str(r["EPS_GAAP"])
      for r in sorted(rs, key=lambda x: x["PeriodEnd"])
    )
    parts.append(tag + " filled " + str(len(rs)) + " (" + bits + ")")
  return "; ".join(parts)


def _json_span_bit(tag, rows):
  tagged = [r for r in rows if r.get("EPS_GAAP") is not None]
  ends = [r["PeriodEnd"] for r in tagged if r.get("PeriodEnd")]
  if not ends:
    return str(tag) + " 0 quarters"
  return (
    str(tag) + " " + str(len(tagged)) + " quarters "
    + min(ends) + ".." + max(ends)
  )


def _log_missing_after_json(ticker):
  _say(ticker, _missing_after_line("JSON", last_missing_after_json))


def _log_ladder(ticker, leftover=None):
  """Stdout + log: the rungs actually taken for this ticker."""
  _say(ticker, "Ladder followed:")
  prev = None
  n = 0
  for group, name, status, detail in last_ladder:
    if group != prev:
      if prev == "JSON":
        n = len(last_missing_after_json or [])
        if n:
          logging.info(
            ticker + "      Missing after JSON (#" + str(n) + "): "
            + ", ".join(last_missing_after_json)
          )
        else:
          logging.info(ticker + "      Missing after JSON (#0): none")
      logging.info(ticker + "    " + _group_header(group) + ":")
      prev = group
    n += 1
    extra = " (" + detail + ")" if detail else ""
    logging.info(
      ticker + "      " + str(n) + ". " + name + " -> " + status + extra
    )
  if prev == "JSON":
    n = len(last_missing_after_json or [])
    if n:
      logging.info(
        ticker + "      Missing after JSON (#" + str(n) + "): "
        + ", ".join(last_missing_after_json)
      )
    else:
      logging.info(ticker + "      Missing after JSON (#0): none")
  if leftover:
    bang = "*" * 26
    logging.error(
      bang + "  " + ticker + "  Leftover missing: "
      + ", ".join(leftover) + "  " + bang
    )
  elif last_ladder:
    logging.info(ticker + "    Leftover missing: none")


def _make_q4_row(ticker, fy, q4_start, q4_end_iso, q4_val, concept_label, source):
  fy_end = parse_iso(fy["PeriodEnd"])
  fy_year, qn = _fiscal_year_and_quarter(fy_end)
  return {
    "Ticker": ticker,
    "Year": fy_year,
    "Quarter": qn,
    "PeriodStart": q4_start.isoformat(),
    "PeriodEnd": q4_end_iso,
    "EPS_GAAP": q4_val,
    "EPS_Concept": concept_label,
    "Source": source,
    "Form": fy["Form"],
    "Filed": fy["Filed"],
    "AccessionNumber": fy["AccessionNumber"],
    "Unit": fy["Unit"],
    "_filed_dt": fy.get("_filed_dt"),
  }


def _q4_looks_like_share_count_break(fy_val, qvals, q4_val):
  """True when FY-sum Q4 is implausible (IPO / share-count change)."""
  if fy_val is None or q4_val is None or not qvals:
    return True
  if any(v is None for v in qvals):
    return True
  abs_q = [abs(v) for v in qvals]
  max_q = max(abs_q)
  min_q = min(abs_q)
  if max_q > 0:
    same_sign = all((v >= 0) == (qvals[0] >= 0) for v in qvals)
    if same_sign and (q4_val >= 0) != (qvals[0] >= 0):
      return True
    if abs(q4_val) > 2.5 * max_q and abs(q4_val) > abs(fy_val):
      return True
  if min_q > 1e-9 and max_q / min_q >= 8:
    return True
  return False


def _apply_q4_from_fy(quarterly, annual, ticker, concept_label, ytd_rows=None):
  """Add missing Q4 rows from FY - (Q1+Q2+Q3), or FY - 9-month YTD."""
  ytd_rows = ytd_rows or []
  q_by_end = {r["PeriodEnd"]: r for r in quarterly}
  q4_cannot = []
  q4_cannot_ends = []

  for fy in annual:
    fy_start = parse_iso(fy["PeriodStart"])
    fy_end = parse_iso(fy["PeriodEnd"])
    q4_end_iso = fy_end.isoformat()
    if fy["EPS_GAAP"] is None:
      logging.debug(
        "[" + ticker + "] FY " + fy["PeriodEnd"]
        + " has no EPS_GAAP, skip Q4 compute"
      )
      continue
    if q4_end_iso in q_by_end:
      logging.debug("[" + ticker + "] Q4 already tagged for " + q4_end_iso)
      continue

    qs_in_fy = [
      r for r in quarterly
      if fy_start <= parse_iso(r["PeriodStart"])
      and parse_iso(r["PeriodEnd"]) <= fy_end
      and r["EPS_GAAP"] is not None
    ]
    qs_in_fy = _dedupe_by_period_end(qs_in_fy)
    qs_in_fy.sort(key=lambda r: r["PeriodEnd"])
    if len(qs_in_fy) == 3:
      q4_start = parse_iso(qs_in_fy[-1]["PeriodEnd"]) + timedelta(days=1)
      q4_val = round(
        fy["EPS_GAAP"] - sum(r["EPS_GAAP"] for r in qs_in_fy),
        4,
      )
      qvals = [r["EPS_GAAP"] for r in qs_in_fy]
      if _q4_looks_like_share_count_break(fy["EPS_GAAP"], qvals, q4_val):
        msg = (
          "[" + ticker + "] skip Q4 compute for FY " + fy["PeriodEnd"]
          + ": implied Q4=" + str(q4_val)
          + " looks like share-count break (FY="
          + str(fy["EPS_GAAP"]) + " quarters=" + str(qvals) + ")"
        )
        _say(
          ticker,
          "Skip Q4 compute for " + fy["PeriodEnd"]
          + " (share-count / IPO guard); implied=" + str(q4_val),
        )
        logging.debug(msg)
        q4_cannot.append(msg)
        q4_cannot_ends.append(fy["PeriodEnd"])
        continue
      logging.debug(
        "[" + ticker + "] computed Q4 " + q4_start.isoformat() + ".." + q4_end_iso
        + " val=" + str(q4_val)
        + " from FY=" + str(fy["EPS_GAAP"])
        + " minus " + str([r["EPS_GAAP"] for r in qs_in_fy])
      )
      q4_row = _make_q4_row(
        ticker, fy, q4_start, q4_end_iso, q4_val, concept_label,
        "Computed(FY-Q1-Q2-Q3)",
      )
      quarterly.append(q4_row)
      q_by_end[q4_end_iso] = q4_row
      last_q4_computes.append({
        "kind": "FY-Q1-Q2-Q3",
        "end": q4_end_iso,
        "val": q4_val,
        "fy": fy,
        "quarters": list(qs_in_fy),
        "ytd": None,
      })
      continue

    ytd_hit = None
    for y in ytd_rows:
      if y.get("EPS_GAAP") is None:
        continue
      if y["PeriodStart"] != fy["PeriodStart"]:
        continue
      q4_start = parse_iso(y["PeriodEnd"]) + timedelta(days=1)
      try:
        stub = duration_days(q4_start.isoformat(), q4_end_iso)
      except Exception:
        continue
      if is_quarterly_duration(stub):
        ytd_hit = y
        break
    if ytd_hit is not None:
      q4_start = parse_iso(ytd_hit["PeriodEnd"]) + timedelta(days=1)
      q4_val = round(fy["EPS_GAAP"] - ytd_hit["EPS_GAAP"], 4)
      if _q4_looks_like_share_count_break(
        fy["EPS_GAAP"], [ytd_hit["EPS_GAAP"]], q4_val
      ):
        msg = (
          "[" + ticker + "] skip Q4 compute (FY-9mo) for FY "
          + fy["PeriodEnd"] + ": implied Q4=" + str(q4_val)
          + " looks like share-count break"
        )
        _say(
          ticker,
          "Skip Q4 compute for " + fy["PeriodEnd"]
          + " (share-count / IPO guard, FY-9mo); implied=" + str(q4_val),
        )
        logging.debug(msg)
        q4_cannot.append(msg)
        q4_cannot_ends.append(fy["PeriodEnd"])
        continue
      logging.debug(
        "[" + ticker + "] computed Q4 " + q4_start.isoformat() + ".." + q4_end_iso
        + " val=" + str(q4_val)
        + " from FY=" + str(fy["EPS_GAAP"])
        + " minus 9mo=" + str(ytd_hit["EPS_GAAP"])
      )
      q4_row = _make_q4_row(
        ticker, fy, q4_start, q4_end_iso, q4_val, concept_label,
        "Computed(FY-9mo)",
      )
      quarterly.append(q4_row)
      q_by_end[q4_end_iso] = q4_row
      last_q4_computes.append({
        "kind": "FY-9mo",
        "end": q4_end_iso,
        "val": q4_val,
        "fy": fy,
        "quarters": [],
        "ytd": ytd_hit,
      })
      continue

    msg = (
      "[" + ticker + "] cannot compute Q4 for FY " + fy["PeriodEnd"]
      + ": tagged quarters=" + str(len(qs_in_fy))
      + " (need 3: Q1+Q2+Q3 or a 9-month YTD)"
      + "; have " + str([r["PeriodEnd"] for r in qs_in_fy])
    )
    logging.debug(msg)
    q4_cannot.append(msg)
    q4_cannot_ends.append(fy["PeriodEnd"])

  last_q4_cannot_ends.clear()
  last_q4_cannot_msgs.clear()
  if quarterly:
    last_q4_cannot_ends.extend(q4_cannot_ends)
    last_q4_cannot_msgs.extend(q4_cannot)
  return quarterly


def _emit_q4_warnings():
  for msg in last_q4_cannot_msgs:
    logging.debug(msg)


def _filled_eps_bit(r):
  """PeriodEnd=value (Form filed YYYY-MM-DD) for fill stdout."""
  bit = r["PeriodEnd"] + "=" + str(r["EPS_GAAP"])
  form = r.get("Form")
  filed = r.get("Filed")
  extra = []
  if form:
    extra.append(str(form))
  if filed:
    extra.append("filed " + str(filed))
  if extra:
    bit += " (" + " ".join(extra) + ")"
  return bit


def _fact_origin(row):
  """Short 'from where' for a tagged fact used in a Q4 compute."""
  src = str(row.get("Source") or "")
  if src.startswith("HTML"):
    method = src
  elif src.startswith("XBRL(10-Q/K)") or src.startswith("XBRL(20-F)"):
    method = INSTANCE_XBRL_LADDER
  elif src.startswith("Computed"):
    method = src
  else:
    method = last_json_method or src or "JSON"
  parts = [method]
  if row.get("Form"):
    parts.append(str(row["Form"]))
  if row.get("Filed"):
    parts.append("filed " + str(row["Filed"]))
  return " ".join(parts)


def _log_q4_computes(ticker):
  """Warn on each last-resort Q4 compute so a missed 8-K is easy to spot."""
  for c in last_q4_computes:
    fy = c["fy"]
    fy_bit = (
      "FY " + fy["PeriodEnd"] + "=" + str(fy["EPS_GAAP"])
      + " (" + _fact_origin(fy) + ")"
    )
    if c["kind"] == "FY-9mo" and c.get("ytd") is not None:
      y = c["ytd"]
      detail = (
        c["end"] + "=" + str(c["val"])
        + " from " + fy_bit
        + " minus 9-month " + y["PeriodStart"] + ".." + y["PeriodEnd"]
        + "=" + str(y["EPS_GAAP"])
        + " (" + _fact_origin(y) + ")"
      )
    else:
      q_bits = []
      for r in c.get("quarters") or []:
        q_bits.append(
          r["PeriodEnd"] + "=" + str(r["EPS_GAAP"])
          + " (" + _fact_origin(r) + ")"
        )
      detail = (
        c["end"] + "=" + str(c["val"])
        + " from " + fy_bit
        + " minus Q1+Q2+Q3: " + "; ".join(q_bits)
      )
    _warn(
      ticker,
      "Q4 compute (last resort — verify 8-K was not missed): " + detail,
    )
  last_q4_computes.clear()


def _primary_source_label(method):
  """Human name for the primary ladder hit (companyconcept / facts / instance)."""
  m = str(method or "")
  if m == "companyconcept":
    return "companyconcept JSON"
  if m == "companyfacts":
    return "companyfacts JSON"
  if m.startswith("xbrl"):
    return INSTANCE_XBRL_LADDER
  return m or "primary"


def _log_json_success(ticker, method, tag, rows):
  src = _primary_source_label(method)
  tagged = [r for r in rows if r.get("EPS_GAAP") is not None]
  if tagged:
    ends = [r["PeriodEnd"] for r in tagged if r.get("PeriodEnd")]
    span = (min(ends) + ".." + max(ends)) if ends else ""
    _say(
      ticker,
      src + " tag " + str(tag) + " produced "
      + str(len(tagged)) + " ~90-day EPS quarters " + span,
    )
  else:
    _say(
      ticker,
      src + " tag " + str(tag) + " returned no ~90-day EPS quarters",
    )


def extract_quarterly_rows(facts_json, ticker, concept_label, reset_globals=True):
  """Return tagged ~90-day EPS rows. Do not compute Q4 here.

  Untagged Q4s are filled later in _finalize_rows: 10-Q XML, then 8-K / 6-K
  HTML, then 10-K / 20-F XML, then 10-K HTML, then FY-(Q1+Q2+Q3) last.
  Computing Q4 from FY before 8-K/6-K is wrong after an IPO share-count
  change (HNGE).
  """
  if reset_globals:
    last_q4_cannot_ends.clear()
    last_q4_cannot_msgs.clear()
    last_annual_rows.clear()
    last_ytd_rows.clear()
    last_q4_computes.clear()
  if not facts_json:
    logging.debug("[" + ticker + "] extract: facts_json is empty")
    return []

  units = facts_json.get("units", {})
  logging.debug(
    "[" + ticker + "] extract concept=" + str(concept_label)
    + " unit_keys=" + str(list(units.keys()))
  )

  quarterly_raw = []
  annual_raw = []
  ytd_raw = []
  other_dur = 0
  skipped_no_dates = 0
  skipped_bad_dates = 0
  for unit_key, entries in units.items():
    if not isinstance(entries, list):
      logging.debug(
        "[" + ticker + "] unit=" + str(unit_key)
        + " is " + type(entries).__name__ + " len=" + str(len(entries))
        + " (expected a list of facts) - skipping"
      )
      continue
    logging.debug(
      "[" + ticker + "] unit=" + str(unit_key) + " raw_facts=" + str(len(entries))
    )
    for e in entries:
      if not (e.get("start") and e.get("end")):
        skipped_no_dates += 1
        continue
      try:
        days = duration_days(e["start"], e["end"])
      except Exception:
        skipped_bad_dates += 1
        continue
      if is_quarterly_duration(days):
        quarterly_raw.append(
          _make_row(ticker, unit_key, e, "XBRL", concept_label)
        )
      elif is_annual_duration(days):
        annual_raw.append(
          _make_row(ticker, unit_key, e, "XBRL", concept_label)
        )
      elif is_nine_month_duration(days):
        ytd_raw.append(
          _make_row(ticker, unit_key, e, "XBRL", concept_label)
        )
      else:
        other_dur += 1
        logging.debug(
          "[" + ticker + "] skip duration=" + str(days)
          + " start=" + str(e.get("start")) + " end=" + str(e.get("end"))
          + " val=" + str(e.get("val")) + " form=" + str(e.get("form"))
        )

  logging.debug(
    "[" + ticker + "] raw quarterly=" + str(len(quarterly_raw))
    + " annual=" + str(len(annual_raw))
    + " nine_month=" + str(len(ytd_raw))
    + " other_duration=" + str(other_dur)
    + " no_dates=" + str(skipped_no_dates)
    + " bad_dates=" + str(skipped_bad_dates)
  )

  quarterly = _dedupe_by_period_end(quarterly_raw)
  annual = _dedupe_by_period_end(annual_raw)
  ytd = _dedupe_by_period_end(ytd_raw)
  logging.debug(
    "[" + ticker + "] after dedupe quarterly=" + str(len(quarterly))
    + " annual=" + str(len(annual))
    + " nine_month=" + str(len(ytd))
  )
  have_fy = {r["PeriodEnd"] for r in last_annual_rows}
  for r in annual:
    if r["PeriodEnd"] not in have_fy:
      last_annual_rows.append(r)
      have_fy.add(r["PeriodEnd"])
  have_ytd = {r["PeriodEnd"] for r in last_ytd_rows}
  for r in ytd:
    if r["PeriodEnd"] not in have_ytd:
      last_ytd_rows.append(r)
      have_ytd.add(r["PeriodEnd"])

  # Do not compute Q4 here. 8-K / 6-K HTML (e.g. HNGE Q4'25 = 0.37) must
  # run before FY-(Q1+Q2+Q3), which can be wrong after an IPO share-count
  # change.
  for r in quarterly:
    r.pop("_filed_dt", None)

  quarterly.sort(key=lambda r: r["PeriodEnd"], reverse=True)
  return quarterly


def fill_missing_q4_from_xbrl(
  cik, ticker, rows, missing_ends, concept_label,
  allowed_forms=None, ladder_name=None,
):
  """Instance XBRL for leftover missing quarter-ends.

  allowed_forms defaults to 10-Q/10-K/20-F. Pass TEN_Q_FORMS or
  ANNUAL_XBRL_FORMS to split the ladder.
  Returns (rows, filled, note) where note is the stdout/ladder detail.
  """
  if not missing_ends:
    return rows, False, ""
  allowed_forms = allowed_forms or FINANCIAL_FORMS
  ladder_name = ladder_name or INSTANCE_XBRL_LADDER
  _say(
    ticker,
    "Trying " + ladder_name + " for " + ", ".join(missing_ends),
  )
  filings = _load_financial_filings(cik, ticker)
  selected = _select_gapfill_filings(
    filings, missing_ends, allowed_forms=allowed_forms
  )
  tally = _form_tally(selected)
  logging.debug(
    "[" + ticker + "] " + ladder_name + " selected=" + str(len(selected))
    + " reports=" + str([f.get("form") + ":" + str(f.get("report")) for f in selected])
  )
  if not selected:
    note = "no " + ladder_name + " matched " + ", ".join(missing_ends)
    _say(ticker, note)
    return rows, False, note

  by_tag, parsed_ok, no_xml = _eps_entries_from_filings(cik, ticker, selected)
  if parsed_ok == 0:
    note = (
      "opened " + tally
      + "; parsed 0/" + str(len(selected))
      + " (no_xml=" + str(no_xml)
      + "); still missing " + ", ".join(missing_ends)
    )
    _say(ticker, ladder_name + " -> " + note)
    return rows, False, note

  have = {r["PeriodEnd"] for r in rows}
  windows = [_fiscal_window(pe) for pe in missing_ends]
  added = []
  used_tags = []
  tags_to_try = []
  for tag, lab in EPS_TAG_PRIORITY:
    if lab == concept_label:
      tags_to_try.append((tag, lab))
  for tag, lab in EPS_TAG_PRIORITY:
    if (tag, lab) not in tags_to_try:
      tags_to_try.append((tag, lab))
  for tag, label in tags_to_try:
    entries = by_tag.get(tag) or []
    if not entries:
      continue
    picked, class_label = _pick_stock_class(entries)
    cand = []
    for e in picked:
      if not (e.get("start") and e.get("end")):
        continue
      try:
        days = duration_days(e["start"], e["end"])
      except Exception:
        continue
      if not is_quarterly_duration(days):
        continue
      end = e["end"]
      if end in have:
        continue
      try:
        end_d = parse_iso(end)
      except Exception:
        continue
      if not any(a <= end_d <= b for a, b in windows):
        continue
      e_copy = dict(e)
      e_copy.pop("_dims", None)
      xbrl_src = (
        "XBRL(20-F)" if str(e.get("form") or "").startswith("20-F")
        else "XBRL(10-Q/K)"
      )
      cand.append(_make_row(ticker, "USD/shares", e_copy, xbrl_src, label))
    cand = _dedupe_by_period_end(cand)
    if cand:
      added.extend(cand)
      used_tags.append(tag + "/" + class_label)
      for r in cand:
        have.add(r["PeriodEnd"])

  if not added:
    note = (
      "opened " + tally
      + "; parsed " + str(parsed_ok)
      + "; no 3-month EPS for " + ", ".join(missing_ends)
    )
    _say(ticker, ladder_name + " -> " + note)
    return rows, False, note

  fill_bits = "; ".join(_filled_eps_bit(r) for r in added)
  note = fill_bits + " [opened " + tally + "]"
  _say(
    ticker,
    ladder_name + " (" + ",".join(used_tags) + ") filled "
    + str(len(added)) + " quarter(s): " + fill_bits,
  )
  return rows + added, True, note


# 8-K / 6-K Exhibit 99.1 HTML — parse rules (flexible; add synonyms here,
# do not add ticker-specific branches).
#   1. Want GAAP diluted EPS for the CURRENT quarter the release is about.
#   2. Row labels: "diluted EPS", "GAAP diluted", "net loss per share …
#      diluted", and "basic and diluted" (same number when anti-dilutive).
#      Skip non-GAAP / adjusted.
#   3. Columns: "three months ended" / "quarter ended" = quarter.
#      "year(s) ended" / "twelve months ended" / "full year ended" = FY.
#      "six/nine months ended" = YTD, not a quarter. FY must not be stored
#      as Q4 (KNSA 2022: 0.06 quarter vs 2.60 year, same December 31).
#   4. Workiva splits '$', '(0.79', ')' across cells — stitch them.
#   5. Per exhibit keep the latest year only (YoY column is last year).
#   6. A filing may fill a period-end only if filed 0-100 days after it
#      (a 2024 8-K is not the source for 2022 Q4).
#   7. 8-K reportDate is often the event day, not the quarter-end.
#
def _is_non_gaap_label(label):
  raw = str(label).lower()
  t = re.sub(r"[^a-z]+", " ", raw).strip()
  if "non-gaap" in raw or "non gaap" in t:
    return True
  if "adjusted" in t and "gaap" not in t:
    return True
  return False


def _is_gaap_diluted_eps_label(label):
  """GAAP diluted EPS row, including 'GAAP EPS' and 'diluted EPS' wording."""
  if _is_non_gaap_label(label):
    return False
  t = re.sub(r"[^a-z]+", " ", str(label).lower()).strip()
  if "basic" in t and "diluted" not in t:
    return False
  has_eps = (
    "eps" in t
    or "per share" in t
    or "earnings per" in t
    or "loss per" in t
  )
  if "diluted" in t and (has_eps or "share" in t or "per" in t):
    return True
  if "basic and diluted" in t or "basic diluted" in t:
    if has_eps or "share" in t or "per" in t:
      return True
  if "gaap" in t and has_eps:
    return True
  return False


def _row_is_gaap_diluted(df, r):
  """True if this row is GAAP diluted EPS, including a child 'Diluted' row."""
  if _is_gaap_diluted_eps_label(df.iat[r, 0]):
    return True
  t = re.sub(r"[^a-z]+", " ", str(df.iat[r, 0]).lower()).strip()
  if t not in (
    "diluted",
    "diluted eps",
    "eps diluted",
    "basic and diluted",
    "basic diluted",
  ):
    return False
  for pr in range(r - 1, max(-1, r - 4), -1):
    parent = str(df.iat[pr, 0])
    pt = re.sub(r"[^a-z]+", " ", parent.lower()).strip()
    if not pt or pt == "nan":
      continue
    if "non-gaap" in parent.lower() or "non gaap" in pt:
      return False
    if (
      ("net income" in pt or "net loss" in pt or "earnings" in pt)
      and ("share" in pt or "eps" in pt or "per" in pt)
    ):
      return True
    break
  return False


def _parse_eps_from_row_col(df, r, c):
  """EPS in this cell, or stitched from '$' / '(0.79' / ')' split cells."""
  val = _parse_eps_cell(df.iat[r, c])
  if val is not None:
    return val
  parts = []
  for j in range(c, min(c + 4, df.shape[1])):
    s = str(df.iat[r, j]).strip().replace("\xa0", " ")
    if s.lower() in ("", "nan", "none"):
      if parts:
        break
      continue
    parts.append(s)
    val = _parse_eps_cell("".join(parts))
    if val is not None:
      return val
  return None


def _quarter_end_date(year, md):
  try:
    return date(year, md[0], md[1])
  except ValueError:
    try:
      return date(year, md[0], calendar.monthrange(year, md[0])[1])
    except Exception:
      return None


def _year_from_cell(x):
  y = _as_year(x)
  if y:
    return y
  m = re.search(r"\b(20\d{2})\b", str(x))
  if m:
    return int(m.group(1))
  return None


def _header_period_kind(cell):
  cl = str(cell).lower().replace("-", " ")
  if re.search(
    r"\b(?:twelve|12)\s+months?\s+ended\b"
    r"|\b(?:fiscal\s+year|full\s+year|years?|yr)\s+ended\b",
    cl,
  ):
    return "fy"
  if re.search(
    r"\b(?:three|3)\s+months?\s+(?:period\s+)?ended\b"
    r"|\bquarter(?:ly)?\s+ended\b",
    cl,
  ):
    return "q"
  if re.search(r"\b(?:six|nine|6|9)\s+months?\s+ended\b", cl):
    return "other"
  return None


def _table_quarter_col_ends(df):
  """Map column index -> period-end date for quarter (not FY) columns.

  Workiva/Excel 8-Ks split 'Three Months Ended' / 'December 31,' / '2021'
  across header rows, and pandas repeats the merged header in every child
  column. Collect kind, month-day, and year independently, then keep only
  three-months / quarter-ended columns.
  """
  nhead = min(12, len(df))
  metas = []
  for c in range(len(df.columns)):
    kinds = []
    md = None
    year = None
    for r in range(nhead):
      cell = str(df.iat[r, c])
      k = _header_period_kind(cell)
      if k:
        kinds.append(k)
      got = _month_day_from_cell(cell)
      if got:
        md = got
      y = _year_from_cell(cell)
      if y:
        year = y
    if "fy" in kinds:
      kind = "fy"
    elif "other" in kinds:
      kind = "other"
    elif "q" in kinds:
      kind = "q"
    else:
      kind = None
    metas.append([c, kind, md, year])
  last_q_md = None
  in_q = False
  for i, row in enumerate(metas):
    _c, kind, md, year = row
    if kind == "q":
      in_q = True
      last_q_md = md or last_q_md
      if md is None and last_q_md:
        row[2] = last_q_md
    elif kind == "fy":
      in_q = False
      last_q_md = None
    elif kind is None and in_q:
      row[1] = "q"
      row[2] = md or last_q_md
  col_end = {}
  for i, (c, kind, md, year) in enumerate(metas):
    if kind != "q" or not md:
      continue
    if not year:
      for c2, k2, md2, y2 in metas[i:i + 4] + metas[max(0, i - 3):i]:
        if k2 == "q" and md2 == md and y2:
          year = y2
          break
    if not year:
      continue
    end_d = _quarter_end_date(year, md)
    if end_d:
      col_end[c] = end_d
  return col_end


def _read_html_tables(html):
  try:
    return pd.read_html(io.BytesIO(html.encode("utf-8")), flavor="lxml")
  except Exception:
    pass
  html2 = re.sub(r"<\?xml[^>]*\?>", "", html)
  try:
    return pd.read_html(io.StringIO(html2), flavor="lxml")
  except Exception:
    return []


def _html_to_text(html):
  t = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html)
  t = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", t)
  t = re.sub(r"(?s)<[^>]+>", " ", t)
  t = (
    t.replace("\xa0", " ")
    .replace("&nbsp;", " ")
    .replace("&#9;", " ")
    .replace("&amp;", "&")
  )
  t = re.sub(r"&#x[0-9a-fA-F]+;", " ", t)
  t = re.sub(r"&#\d+;", " ", t)
  t = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", t)
  t = re.sub(r"\s+", " ", t)
  # Workiva exhibits insert spaces inside words, years, and EPS:
  # "d iluted", "n on-GAAP", "20 2 1", "$0. 14"
  for word in ("diluted", "gaap", "earnings", "quarter"):
    pat = r"\b" + r"\s*".join(re.escape(ch) for ch in word) + r"\b"
    t = re.sub(pat, word, t, flags=re.I)
  t = re.sub(r"\bn\s*o\s*n\s*[\s-]*g\s*a\s*a\s*p\b", "non-gaap", t, flags=re.I)
  t = re.sub(r"\b20\s*([0-9])\s*([0-9])\b", r"20\1\2", t)
  t = re.sub(r"\$\s*(\d+)\s*\.\s*(\d+)\b", r"$\1.\2", t)
  return t


def _calendar_q_end(q, year):
  """Q1-Q4 of fiscal year `year` (the calendar year of FYE)."""
  md = (last_fye.month, last_fye.day) if last_fye else (12, 31)
  day = min(md[1], calendar.monthrange(year, md[0])[1])
  fy_end = date(year, md[0], day)
  if q == 4:
    return fy_end
  return _add_months_clamped(fy_end, -3 * (4 - q))


_ORD_QUARTER = {
  "first": 1, "1st": 1, "second": 2, "2nd": 2,
  "third": 3, "3rd": 3, "fourth": 4, "4th": 4,
}


def _default_q_end_from_8k_text(text):
  """Quarter-end from the exhibit headline, e.g. Q4 ended December 31, 2021."""
  head = text[:2500]
  m = re.search(
    r"(?:first|1st|second|2nd|third|3rd|fourth|4th)\s+quarter"
    r"(?:\s+and\s+(?:full\s+)?year)?"
    r"(?:\s+results)?"
    r"(?:\s+for(?:\s+the)?)?"
    r"(?:\s+(?:the\s+)?(?:fourth|4th|first|1st|second|2nd|third|3rd)\s+quarter)?"
    r"(?:\s+and\s+(?:full\s+)?year)?"
    r"\s+ended\s+"
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+"
    r"(\d{1,2})\s*,\s*(20\d{2})",
    head,
    re.I,
  )
  if m:
    month = _MONTH_PREFIX.get(m.group(1)[:3].lower())
    if month:
      return _quarter_end_date(int(m.group(3)), (month, int(m.group(2))))
  m = re.search(
    r"(first|1st|second|2nd|third|3rd|fourth|4th)\s+quarter\s+(20\d{2})",
    head,
    re.I,
  )
  if m:
    return _calendar_q_end(_ORD_QUARTER[m.group(1).lower()], int(m.group(2)))
  m = re.search(r"\bq([1-4])\s+(20\d{2})\b", head, re.I)
  if m:
    return _calendar_q_end(int(m.group(1)), int(m.group(2)))
  m = re.search(
    r"(?:three\s+months|quarter)\s+ended\s+"
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+"
    r"(\d{1,2})\s*,\s*(20\d{2})",
    head,
    re.I,
  )
  if m:
    month = _MONTH_PREFIX.get(m.group(1)[:3].lower())
    if month:
      return _quarter_end_date(int(m.group(3)), (month, int(m.group(2))))
  return None


def _period_end_from_eps_window(window, default_end=None):
  """Quarter-end for a prose EPS mention.

  Prefer the latest year. An 8-K's current figure is the newest period
  the company is reporting; older years in the same sentence are
  comparatives ('vs Q4 2020') and must not take that number.
  """
  window = re.split(
    r"\bcompared to\b|\bversus\b|\bvs\.?\b", window, flags=re.I
  )[0]
  cands = []
  if default_end is not None:
    cands.append(default_end)
  for qm in re.finditer(r"\bq([1-4])\s+(20\d{2})\b", window, re.I):
    cands.append(_calendar_q_end(int(qm.group(1)), int(qm.group(2))))
  for qm in re.finditer(
    r"(first|1st|second|2nd|third|3rd|fourth|4th)\s+quarter"
    r"\s+(?:of\s+)?(20\d{2})",
    window,
    re.I,
  ):
    cands.append(
      _calendar_q_end(_ORD_QUARTER[qm.group(1).lower()], int(qm.group(2)))
    )
  dm = re.search(
    r"(?:quarter|three\s+months)\s+(?:and\s+(?:full\s+)?year\s+)?ended\s+"
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+"
    r"(\d{1,2})\s*,\s*(20\d{2})",
    window,
    re.I,
  )
  if dm:
    month = _MONTH_PREFIX.get(dm.group(1)[:3].lower())
    if month:
      cands.append(_quarter_end_date(int(dm.group(3)), (month, int(dm.group(2)))))
  cands = [d for d in cands if d is not None]
  if not cands:
    return None
  return max(cands)


def _looks_like_annual_eps_window(window, after=""):
  """True if this EPS mention is the full year, not the quarter."""
  near = (window[-160:] if len(window) > 160 else window) + " " + after[:48]
  if re.search(
    r"\b(?:for the year|full year|years? ended|twelve months|annual)\b",
    near,
    re.I,
  ):
    if not re.search(r"\b(?:quarter|three\s+months|q[1-4])\b", near, re.I):
      return True
  return False


def _span_has_non_gaap(text, start, end):
  left = text[max(0, start - 28):start]
  mid = text[start:end]
  return bool(re.search(r"non[\s-]*gaap", left + " " + mid, re.I))


def _record_8k_eps(found, end_d, val):
  if end_d is None or val is None:
    return
  if abs(val) > 50:
    return
  found.setdefault(end_d.isoformat(), val)


def _keep_latest_year_for_duplicate_eps(found):
  """If the same EPS was tagged to several years, keep the latest year.

  Tables already bind each column to a year. This is for prose, where
  '$0.14 ... fourth quarter of 2020' would otherwise copy current EPS
  onto a comparative year.
  """
  by_val = {}
  for iso, val in found.items():
    by_val.setdefault(val, []).append(iso)
  drop = []
  for _val, isos in by_val.items():
    if len(isos) < 2:
      continue
    isos.sort()
    drop.extend(isos[:-1])
  for iso in drop:
    del found[iso]


def _parse_8k_gaap_diluted_from_text(html):
  """GAAP diluted EPS from exhibit text.

  Companies word this many ways: 'GAAP diluted EPS was $0.14',
  'diluted EPS for the fourth quarter was $0.14',
  '$0.14 GAAP diluted EPS', FOUR-style recon tables, etc.
  Skip non-GAAP / adjusted and full-year figures.
  When several years appear, keep the latest year (current report).
  """
  found = {}
  text = _html_to_text(html)
  default_end = _default_q_end_from_8k_text(text)
  m = re.search(
    r"reconciliation of gaap diluted eps to non-gaap eps\s+"
    r"(?P<heads>(?:(?:q[1-4]|fy)\s+20\d{2}\s+)+)"
    r"gaap diluted eps\s+"
    r"(?P<vals>(?:" + _MONEY_TOKEN + r"\s+)+)",
    text,
    re.I,
  )
  if m:
    heads = re.findall(r"(q[1-4]|fy)\s+(20\d{2})", m.group("heads"), re.I)
    vals = re.findall(_MONEY_TOKEN, m.group("vals"))
    for (kind, year_s), tok in zip(heads, vals):
      if kind.lower() == "fy":
        continue
      v = _money_token_value(tok)
      if v is None:
        continue
      found[_calendar_q_end(int(kind[1]), int(year_s)).isoformat()] = v
  for m in re.finditer(
    r"(" + _MONEY_TOKEN + r")\s+gaap\s+diluted\s+eps\b", text, re.I
  ):
    if _span_has_non_gaap(text, m.start(), m.end()):
      continue
    window = text[max(0, m.start() - 400):m.start()]
    after = text[m.end():m.end() + 48]
    if _looks_like_annual_eps_window(window, after):
      continue
    end_d = _period_end_from_eps_window(window, default_end)
    _record_8k_eps(found, end_d, _money_token_value(m.group(1)))
  for m in re.finditer(
    r"(?P<label>(?:gaap\s+)?(?:diluted\s+)?(?:gaap\s+)?"
    r"(?:earnings\s+per\s+share(?:\s*\([^)]{0,24}\))?|"
    r"eps|"
    r"earnings\s+per\s+diluted\s+share))"
    r"\s+(?:was|were|of|:)\s+(?P<val>" + _MONEY_TOKEN + r")",
    text,
    re.I,
  ):
    if _span_has_non_gaap(text, m.start(), m.end()):
      continue
    lab = re.sub(r"[^a-z]+", " ", m.group("label").lower()).strip()
    if "gaap" not in lab and "diluted" not in lab:
      continue
    if "basic" in lab and "diluted" not in lab:
      continue
    window = text[max(0, m.start() - 500):m.start()]
    after = text[m.end():m.end() + 48]
    if _looks_like_annual_eps_window(window, after):
      continue
    end_d = _period_end_from_eps_window(window, default_end)
    _record_8k_eps(found, end_d, _money_token_value(m.group("val")))
  for m in re.finditer(
    r"diluted\s+(?:earnings\s+per\s+share|eps)\s+for\s+the\s+"
    r"(?:(?P<ord>first|1st|second|2nd|third|3rd|fourth|4th)\s+)?"
    r"quarter\s+was\s+(?P<val>" + _MONEY_TOKEN + r")",
    text,
    re.I,
  ):
    if _span_has_non_gaap(text, m.start(), m.end()):
      continue
    window = text[max(0, m.start() - 800):m.start()]
    after = text[m.end():m.end() + 48]
    if _looks_like_annual_eps_window(window, after):
      continue
    end_d = _period_end_from_eps_window(window, default_end)
    if end_d is None and m.group("ord") and default_end is not None:
      end_d = _calendar_q_end(
        _ORD_QUARTER[m.group("ord").lower()], default_end.year
      )
    _record_8k_eps(found, end_d, _money_token_value(m.group("val")))
  _keep_latest_year_for_duplicate_eps(found)
  return found


_MONEY_TOKEN = r"\$\s*(?:\(\s*\d+\.\d+\s*\)|-?\d+\.\d+)"


def _money_token_value(tok):
  return _parse_eps_cell(tok)


def _parse_8k_gaap_diluted_quarters(html):
  """Map period-end ISO -> GAAP diluted EPS from an earnings 8-K exhibit.

  Tables first (column kind = quarter vs FY), then prose. See the 8-K
  parse-rules block above _is_non_gaap_label.
  """
  found = {}
  for df in _read_html_tables(html):
    if df is None or df.empty or df.shape[1] < 3:
      continue
    col_end = _table_quarter_col_ends(df)
    if not col_end:
      continue
    for r in range(len(df)):
      if not _row_is_gaap_diluted(df, r):
        continue
      for c, end_d in col_end.items():
        val = _parse_eps_from_row_col(df, r, c)
        if val is None:
          continue
        iso = end_d.isoformat()
        if iso not in found:
          found[iso] = val
  for end_iso, val in _parse_8k_gaap_diluted_from_text(html).items():
    found.setdefault(end_iso, val)
  return found


def _keep_latest_year_in_parsed(parsed):
  """Drop YoY comparative years when building a series from scratch.

  One 6-K table often has last-year and this-year columns (BSP Q2 2025
  0.11 and Q2 2026 0.28). Keeping both opens interior holes for quarters
  that were never filed.
  """
  years = []
  for end_iso in parsed:
    try:
      years.append(parse_iso(end_iso).year)
    except Exception:
      continue
  if not years:
    return parsed
  latest_y = max(years)
  out = {}
  for end_iso, val in parsed.items():
    try:
      if parse_iso(end_iso).year == latest_y:
        out[end_iso] = val
    except Exception:
      continue
  return out


def fill_missing_from_8k(cik, ticker, rows, missing_ends, concept_label):
  """Fill from 8-K (Item 2.02) / 6-K earnings-release HTML.

  If missing_ends is set, only fill those dates (filings 0-100 days later).
  If missing_ends is empty, walk all 6-Ks and Item 2.02 8-Ks newest-first
  and keep every quarter they contain — no invented lookback dates.
  """
  open_ended = not missing_ends
  if open_ended:
    _say(
      ticker,
      "JSON+10-Q produced no quarters; trying " + CURRENT_HTML_LADDER,
    )
  else:
    _say(
      ticker,
      "Trying " + CURRENT_HTML_LADDER + " for " + ", ".join(missing_ends),
    )
  filings = _load_8k_filings(cik, ticker)
  if open_ended:
    selected = _select_open_ended_current_reports(filings)
    _say(
      ticker,
      CURRENT_HTML_LADDER + " "
      + str(len(selected)) + " 6-K/Item-2.02 8-K filing(s), newest first",
    )
  else:
    selected = _select_8k_for_ends(filings, missing_ends)
  if not selected:
    if open_ended:
      _say(ticker, "No 8-K or 6-K filings")
    else:
      _say(
        ticker,
        "No 8-K or 6-K filing in window for " + ", ".join(missing_ends),
      )
    return rows, False

  want = {}
  for pe in missing_ends:
    try:
      want[pe] = parse_iso(pe)
    except Exception:
      continue
  have = {r["PeriodEnd"] for r in rows}
  added = []
  cik_nolead = str(int(cik))
  for filing in selected:
    accn = filing["accn"]
    accn_nodash = accn.replace("-", "")
    index_url = (
      f"https://www.sec.gov/Archives/edgar/data/{cik_nolead}/{accn_nodash}/index.json"
    )
    try:
      idx_resp = _http_get(index_url, ticker, "8-K/6-K index " + accn)
      if idx_resp.status_code != 200:
        continue
      items = (idx_resp.json().get("directory") or {}).get("item") or []
      names = [it.get("name") for it in items]
      ex_name = _exhibit_99_name(names)
      html = ""
      if ex_name:
        ex_url = (
          f"https://www.sec.gov/Archives/edgar/data/{cik_nolead}/"
          f"{accn_nodash}/{ex_name}"
        )
        ex_resp = _http_get(ex_url, ticker, "8-K/6-K exhibit " + ex_name)
        if ex_resp.status_code == 200:
          html = ex_resp.text
      if not html and filing.get("primary"):
        prim_url = (
          f"https://www.sec.gov/Archives/edgar/data/{cik_nolead}/"
          f"{accn_nodash}/{filing['primary']}"
        )
        prim_resp = _http_get(prim_url, ticker, "8-K/6-K primary")
        if prim_resp.status_code == 200:
          html = prim_resp.text
      if not html:
        continue
      parsed = _parse_8k_gaap_diluted_quarters(html)
      if parsed:
        parsed = _keep_latest_year_in_parsed(parsed)
    except Exception:
      logging.debug(
        "[" + ticker + "] 8-K/6-K parse failed " + accn, exc_info=True
      )
      continue
    logging.debug(
      "[" + ticker + "] 8-K/6-K " + accn + " GAAP diluted quarters="
      + str(parsed)
    )
    filed_iso = (filing.get("filed") or "")[:10]
    try:
      filed_d = parse_iso(filed_iso) if filed_iso else None
    except Exception:
      filed_d = None
    for end_iso, val in parsed.items():
      if end_iso in have:
        continue
      try:
        end_d = parse_iso(end_iso)
      except Exception:
        continue
      if filed_d is not None:
        lag = (filed_d - end_d).days
        if lag < 0 or lag > _8K_FILED_AFTER_MAX_DAYS:
          logging.debug(
            "[" + ticker + "] 8-K/6-K " + accn
            + " skip " + end_iso + "=" + str(val)
            + " (filed " + filed_iso + ", " + str(lag)
            + " days after period; YoY/too old)"
          )
          continue
      matched = None
      if want:
        for pe, want_d in want.items():
          if abs((end_d - want_d).days) <= 10:
            matched = pe
            break
        if not matched:
          continue
      else:
        matched = end_iso
      form = filing.get("form") or "8-K"
      src = "HTML(6-K)" if str(form).startswith("6-K") else "HTML(8-K)"
      fy_year, qn = _fiscal_year_and_quarter(end_d)
      added.append({
        "Ticker": ticker,
        "Year": fy_year,
        "Quarter": qn,
        "PeriodStart": _quarter_start_for_end(end_d).isoformat(),
        "PeriodEnd": end_iso,
        "EPS_GAAP": val,
        "EPS_Concept": concept_label or "Diluted",
        "Source": src,
        "Form": form,
        "Filed": filing.get("filed"),
        "AccessionNumber": accn,
        "Unit": "USD/shares",
      })
      have.add(end_iso)

  if not added:
    if open_ended:
      _say(
        ticker,
        CURRENT_HTML_LADDER + " had no GAAP diluted EPS",
      )
    else:
      _say(
        ticker,
        CURRENT_HTML_LADDER + " had no GAAP diluted EPS for "
        + ", ".join(missing_ends),
      )
    return rows, False
  added.sort(key=lambda r: r["PeriodEnd"])
  _say(
    ticker,
    CURRENT_HTML_LADDER + " filled "
    + str(len(added)) + " quarter(s): "
    + "; ".join(_filled_eps_bit(r) for r in added),
  )
  return rows + added, True


_MONTH_PREFIX = {
  "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
  "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
_MONTH_DAY_RE = re.compile(
  r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})",
  re.I,
)
_YEAR_RE = re.compile(r"^20\d{2}(?:\.0+)?$")


def _parse_eps_cell(x):
  if x is None:
    return None
  try:
    if pd.isna(x):
      return None
  except Exception:
    pass
  s = str(x).strip().replace("\xa0", " ").replace(",", "")
  if s.lower() in ("", "nan", "-", "—", "–", "$", "none"):
    return None
  s = s.replace("$", "").strip()
  neg = False
  if s.startswith("("):
    neg = True
    s = s[1:]
    if s.endswith(")"):
      s = s[:-1]
    s = s.strip()
  try:
    val = float(s)
  except ValueError:
    return None
  if abs(val) > 500:
    return None
  return -val if neg else val


def _month_day_from_cell(x):
  m = _MONTH_DAY_RE.search(str(x))
  if not m:
    return None
  month = _MONTH_PREFIX.get(m.group(1)[:3].lower())
  if not month:
    return None
  return month, int(m.group(2))


def _as_year(x):
  s = str(x).strip()
  if _YEAR_RE.match(s):
    return int(float(s))
  return None


def _is_diluted_eps_label(label):
  t = re.sub(r"[^a-z]+", " ", str(label).lower()).strip()
  if "diluted" not in t:
    return False
  if "share" not in t and "eps" not in t and "per" not in t:
    return False
  return True


def _is_basic_eps_label(label):
  t = re.sub(r"[^a-z]+", " ", str(label).lower()).strip()
  if "basic" not in t or "diluted" in t:
    return False
  if "share" not in t and "eps" not in t and "per" not in t:
    return False
  return True


def _quarter_start_for_end(end_d):
  fy_end = _fye_on_or_after(end_d)
  qs = _fiscal_q_ends_for_fy(fy_end)
  _y, qn = _fiscal_year_and_quarter(end_d)
  if qn <= 1:
    prev = _add_months_clamped(fy_end, -12)
  else:
    prev = qs[qn - 2]
  return prev + timedelta(days=1)


def _period_end_for_fy_col(fy_year, month, day, fy_md):
  fy_month, fy_day = fy_md
  year = fy_year if (month, day) <= (fy_month, fy_day) else fy_year - 1
  try:
    return date(year, month, day)
  except ValueError:
    return None


def _parse_10k_quarterly_tables(html, fy_md):
  """Return list of {end, start, val, concept} from Quarterly Financial Data."""
  try:
    dfs = pd.read_html(io.StringIO(html), flavor="lxml")
  except Exception:
    try:
      dfs = pd.read_html(io.StringIO(html))
    except Exception:
      return []
  found = []
  for df in dfs:
    if df is None or df.empty or df.shape[1] < 4:
      continue
    col_md = {}
    for r in range(min(6, len(df))):
      for c in range(len(df.columns)):
        md = _month_day_from_cell(df.iat[r, c])
        if md:
          col_md[c] = md
    ordered_md = []
    seen_md = set()
    for c in sorted(col_md):
      md = col_md[c]
      if md not in seen_md:
        seen_md.add(md)
        ordered_md.append(md)
    if len(ordered_md) < 3:
      continue
    groups = {md: [c for c, v in col_md.items() if v == md] for md in ordered_md}
    current_year = None
    for r in range(len(df)):
      label = df.iat[r, 0]
      yr = _as_year(label)
      if yr is not None:
        current_year = yr
        continue
      if current_year is None:
        continue
      if _is_diluted_eps_label(label):
        concept = "Diluted"
      elif _is_basic_eps_label(label):
        concept = "Basic"
      else:
        continue
      for md in ordered_md:
        val = None
        for c in groups[md]:
          val = _parse_eps_cell(df.iat[r, c])
          if val is not None:
            break
        if val is None:
          continue
        end_d = _period_end_for_fy_col(current_year, md[0], md[1], fy_md)
        if end_d is None:
          continue
        found.append({
          "end": end_d,
          "start": _quarter_start_for_end(end_d),
          "val": val,
          "concept": concept,
        })
  # Prefer Diluted when both basic and diluted exist for the same end.
  by_end = {}
  for item in found:
    prev = by_end.get(item["end"])
    if prev is None or (prev["concept"] != "Diluted" and item["concept"] == "Diluted"):
      by_end[item["end"]] = item
  return list(by_end.values())


def _select_10k_for_ends(filings, missing_ends):
  missing_ds = []
  for pe in missing_ends:
    try:
      missing_ds.append(parse_iso(pe))
    except Exception:
      continue
  selected = []
  seen = set()
  for f in filings:
    if not _is_annual_report_form(f.get("form")):
      continue
    if not f.get("primary") or not f.get("accn"):
      continue
    rd = (f.get("report") or "")[:10]
    if not rd:
      continue
    try:
      rd_d = parse_iso(rd)
    except Exception:
      continue
    fy_start, fy_end = _fiscal_window(rd)
    try:
      prev = date(fy_end.year - 1, fy_end.month, fy_end.day)
    except ValueError:
      prev = date(fy_end.year - 1, 2, 28)
    prev_start, prev_end = _fiscal_window(prev.isoformat())
    keep = False
    for d in missing_ds:
      if fy_start <= d <= fy_end or prev_start <= d <= prev_end:
        keep = True
        break
      if abs((rd_d - d).days) <= 15:
        keep = True
        break
    if not keep:
      continue
    if f["accn"] in seen:
      continue
    seen.add(f["accn"])
    selected.append(f)
  selected.sort(key=lambda f: f.get("report") or "")
  return selected[:6]


def fill_missing_q4_from_html(cik, ticker, rows, missing_ends, concept_label):
  """Fill missing FY quarters from the 10-K / 20-F HTML quarterly note."""
  if not missing_ends:
    return rows, False
  _say(
    ticker,
    "Trying " + ANNUAL_HTML_LADDER + " quarterly table for "
    + ", ".join(missing_ends),
  )
  filings = _load_financial_filings(cik, ticker)
  selected = _select_10k_for_ends(filings, missing_ends)
  if not selected:
    _say(
      ticker,
      "No 10-K or 20-F HTML filing matched " + ", ".join(missing_ends),
    )
    return rows, False

  windows = [_fiscal_window(pe) for pe in missing_ends]
  # Also allow the next FY so Q1/Q2 holes after a stub year can fill.
  extra = []
  for fy_start, fy_end in windows:
    try:
      nxt = date(fy_end.year + 1, fy_end.month, fy_end.day)
    except ValueError:
      nxt = date(fy_end.year + 1, fy_end.month, fy_end.day - 1)
    extra.append(_fiscal_window(nxt.isoformat()))
  windows = windows + extra

  have = {r["PeriodEnd"] for r in rows}
  added = []
  cik_nolead = str(int(cik))
  for filing in selected:
    accn = filing["accn"]
    accn_nodash = accn.replace("-", "")
    prim = filing["primary"]
    html_url = (
      f"https://www.sec.gov/Archives/edgar/data/{cik_nolead}/"
      f"{accn_nodash}/{prim}"
    )
    try:
      resp = _http_get(html_url, ticker, "10-K/20-F HTML " + accn)
      if resp.status_code != 200 or not resp.text:
        continue
      if last_fye is None:
        logging.error(
          ticker + "  No FYE for 10-K/20-F HTML parse. Stopping."
        )
        sys.exit(1)
      fy_md = (last_fye.month, last_fye.day)
      parsed = _parse_10k_quarterly_tables(resp.text, fy_md)
    except Exception:
      logging.debug(
        "[" + ticker + "] 10-K/20-F HTML parse failed " + accn, exc_info=True
      )
      continue
    logging.debug(
      "[" + ticker + "] HTML " + accn + " quarterly EPS facts=" + str(len(parsed))
    )
    for item in parsed:
      end_iso = item["end"].isoformat()
      if end_iso in have:
        continue
      if not any(a <= item["end"] <= b for a, b in windows):
        continue
      fy_year, qn = _fiscal_year_and_quarter(item["end"])
      added.append({
        "Ticker": ticker,
        "Year": fy_year,
        "Quarter": qn,
        "PeriodStart": item["start"].isoformat(),
        "PeriodEnd": end_iso,
        "EPS_GAAP": item["val"],
        "EPS_Concept": item["concept"],
        "Source": (
          "HTML(20-F quarterly)"
          if str(filing.get("form") or "").startswith("20-F")
          else "HTML(10-K quarterly)"
        ),
        "Form": filing.get("form"),
        "Filed": filing.get("filed"),
        "AccessionNumber": accn,
        "Unit": "USD/shares",
      })
      have.add(end_iso)

  if not added:
    _say(
      ticker,
      ANNUAL_HTML_LADDER + " quarterly table had no EPS for "
      + ", ".join(missing_ends),
    )
    return rows, False

  added.sort(key=lambda r: r["PeriodEnd"])
  want = set(missing_ends)

  def _is_requested(end_iso):
    if end_iso in want:
      return True
    try:
      d = parse_iso(end_iso)
    except Exception:
      return False
    for pe in missing_ends:
      try:
        if abs((d - parse_iso(pe)).days) <= 10:
          return True
      except Exception:
        continue
    return False

  requested = [r for r in added if _is_requested(r["PeriodEnd"])]
  extra = [r for r in added if not _is_requested(r["PeriodEnd"])]
  if requested:
    _say(
      ticker,
      ANNUAL_HTML_LADDER + " filled requested "
      + "; ".join(_filled_eps_bit(r) for r in requested),
    )
  if extra:
    _say(
      ticker,
      ANNUAL_HTML_LADDER + " also filled "
      + str(len(extra)) + " nearby hole(s) from the same 10-K/20-F table: "
      + "; ".join(_filled_eps_bit(r) for r in extra),
    )
  return rows + added, True


def _log_sources(ticker, rows, method, tag):
  """Stdout + log: which quarters came from which source."""
  groups = {}
  for r in rows:
    src = r.get("Source") or "?"
    groups.setdefault(src, []).append(r)
  order = [
    "XBRL",
    "XBRL(10-Q/K)",
    "XBRL(20-F)",
    "HTML(8-K)",
    "HTML(6-K)",
    "Computed(FY-Q1-Q2-Q3)",
    "Computed(FY-9mo)",
    "HTML(10-K quarterly)",
    "HTML(20-F quarterly)",
  ]
  keys = [k for k in order if k in groups]
  keys += [k for k in groups if k not in order]
  json_method = str(method).split("+")[0]
  for src in keys:
    rs = sorted(groups[src], key=lambda x: x["PeriodEnd"])
    if src == "XBRL":
      ends = [r["PeriodEnd"] for r in rs]
      _say(
        ticker,
        "From " + json_method + "/XBRL tag=" + str(tag)
        + ": " + str(len(rs)) + " quarter(s) "
        + ends[0] + ".." + ends[-1],
      )
    else:
      bits = [r["PeriodEnd"] + "=" + str(r["EPS_GAAP"]) for r in rs]
      _say(ticker, "From " + src + ": " + "; ".join(bits))


def _append_method(method, bit):
  return (method + "+" + bit) if method else bit


def _current_html_method_bit(rows):
  """8k / 6k / 8k/6k from the forms we actually filled."""
  has_6k = False
  has_8k = False
  for r in rows:
    src = str(r.get("Source") or "")
    form = str(r.get("Form") or "")
    if src == "HTML(6-K)" or form.startswith("6-K"):
      has_6k = True
    if src == "HTML(8-K)" or form.startswith("8-K"):
      has_8k = True
  if has_6k and has_8k:
    return "8k/6k"
  if has_6k:
    return "6k"
  return "8k"


def _finalize_rows(cik, ticker, rows, method, tag, label, attempts):
  global last_newer_filing_ends
  rows = list(rows) if rows else []
  missing = _still_missing_quarters(rows) if rows else []
  if rows:
    newer_q = _newer_10q_report_ends(cik, ticker, rows)
    newer_k = _newer_8k_report_ends(cik, ticker, rows)
    if newer_q:
      _say(
        ticker,
        "10-Q report date(s) newer than last JSON quarter: "
        + ", ".join(newer_q),
      )
    if newer_k:
      _say(
        ticker,
        "8-K / 6-K earnings newer than last JSON quarter: "
        + ", ".join(newer_k),
      )
    newer = sorted(set(newer_q + newer_k))
    last_newer_filing_ends = list(newer)
    for pe in newer:
      if pe not in missing:
        missing.append(pe)
    missing.sort()
  did_filings = bool(missing) or not rows

  # 3. 10-Q instance XBRL (Q1-Q3 holes; spine if JSON was empty)
  attempts.append("10-Q XBRL")
  if not rows:
    _say(ticker, "Trying " + TEN_Q_XBRL_LADDER)
    q_rows, q_method, q_tag, q_label = try_xbrl_filings(
      cik, ticker, allowed_forms=TEN_Q_FORMS
    )
    if q_rows:
      rows, method = q_rows, q_method
      tag = q_tag or tag
      label = q_label or label
      _ladder_step(
        "filings", TEN_Q_XBRL_LADDER, "hit", _ladder_hit_detail(rows)
      )
    else:
      _ladder_step(
        "filings", TEN_Q_XBRL_LADDER, "miss", "no quarterly EPS"
      )
  elif missing:
    rows, filled, xbrl_note = fill_missing_q4_from_xbrl(
      cik, ticker, rows, missing, label,
      allowed_forms=TEN_Q_FORMS, ladder_name=TEN_Q_XBRL_LADDER,
    )
    if filled:
      method = _append_method(method, "10q-xbrl")
      _ladder_step(
        "filings", TEN_Q_XBRL_LADDER,
        _filled_status(_n_filled_from_note(xbrl_note)), xbrl_note,
      )
    else:
      _ladder_step(
        "filings", TEN_Q_XBRL_LADDER, "no fill",
        xbrl_note or ", ".join(missing),
      )
  else:
    _ladder_step(
      "filings", TEN_Q_XBRL_LADDER, "not needed",
      "no missing quarters after JSON",
    )

  missing = _still_missing_quarters(rows) if rows else []
  if missing:
    _say(ticker, _missing_after_line(TEN_Q_XBRL_LADDER, missing))

  # 4. 8-K / 6-K HTML
  attempts.append("8-K/6-K HTML")
  if missing or not rows:
    rows, filled_8k = fill_missing_from_8k(
      cik, ticker, rows, missing, label
    )
    if filled_8k:
      method = _append_method(method, _current_html_method_bit(rows))
      if not tag:
        tag = "Diluted"
      if not label:
        label = "Diluted"
      missing = _still_missing_quarters(rows) if rows else []
      filled_bits = _ladder_source_bits_any(
        rows, ("HTML(8-K)", "HTML(6-K)")
      )
      detail = filled_bits
      if missing:
        detail += "; still unfilled " + ", ".join(missing)
      _ladder_step(
        "filings", CURRENT_HTML_LADDER,
        _filled_status(_n_filled_from_note(filled_bits)), detail,
      )
    else:
      _ladder_step(
        "filings", CURRENT_HTML_LADDER, "no fill",
        ", ".join(missing) if missing else "no quarterly EPS",
      )
      missing = _still_missing_quarters(rows) if rows else []
    if missing:
      _say(ticker, _missing_after_line(CURRENT_HTML_LADDER, missing))
  else:
    _ladder_step(
      "filings", CURRENT_HTML_LADDER, "not needed",
      "no missing quarters left",
    )

  # 5. 10-K / 20-F instance XBRL
  attempts.append("10-K/20-F XBRL")
  if not rows:
    _say(ticker, "Trying " + ANNUAL_XBRL_LADDER)
    a_rows, a_method, a_tag, a_label = try_xbrl_filings(
      cik, ticker, allowed_forms=ANNUAL_XBRL_FORMS
    )
    if a_rows:
      rows, method = a_rows, a_method
      tag = a_tag or tag
      label = a_label or label
      _ladder_step(
        "filings", ANNUAL_XBRL_LADDER, "hit", _ladder_hit_detail(rows)
      )
    else:
      _ladder_step(
        "filings", ANNUAL_XBRL_LADDER, "miss", "no quarterly EPS"
      )
  elif missing:
    rows, filled, xbrl_note = fill_missing_q4_from_xbrl(
      cik, ticker, rows, missing, label,
      allowed_forms=ANNUAL_XBRL_FORMS, ladder_name=ANNUAL_XBRL_LADDER,
    )
    if filled:
      method = _append_method(method, "10k-xbrl")
      _ladder_step(
        "filings", ANNUAL_XBRL_LADDER,
        _filled_status(_n_filled_from_note(xbrl_note)), xbrl_note,
      )
    else:
      _ladder_step(
        "filings", ANNUAL_XBRL_LADDER, "no fill",
        xbrl_note or ", ".join(missing),
      )
  else:
    _ladder_step(
      "filings", ANNUAL_XBRL_LADDER, "not needed",
      "no missing quarters left",
    )

  missing = _still_missing_quarters(rows) if rows else []
  if missing:
    _say(ticker, _missing_after_line(ANNUAL_XBRL_LADDER, missing))

  # 6. 10-K / 20-F HTML quarterly table (before inventing Q4)
  if missing:
    rows, filled_html = fill_missing_q4_from_html(
      cik, ticker, rows, missing, label
    )
    if filled_html:
      method = _append_method(method, "html-10k")
      html_bits = _ladder_source_bits_any(
        rows, ("HTML(10-K quarterly)", "HTML(20-F quarterly)")
      )
      _ladder_step(
        "filings", ANNUAL_HTML_LADDER,
        _filled_status(_n_filled_from_note(html_bits)), html_bits,
      )
      missing = _still_missing_quarters(rows) if rows else []
      if missing:
        _say(ticker, _missing_after_line(ANNUAL_HTML_LADDER, missing))
    else:
      _ladder_step(
        "filings", ANNUAL_HTML_LADDER, "no fill", ", ".join(missing)
      )
  elif did_filings or rows:
    _ladder_step(
      "filings", ANNUAL_HTML_LADDER, "not needed",
      "no missing quarters left",
    )

  missing = _still_missing_quarters(rows) if rows else []

  # 7. FY - (Q1+Q2+Q3) last resort only — 8-K almost always has Q4
  if rows:
    missing_before_compute = list(missing)
    rows = _apply_q4_from_fy(
      rows, last_annual_rows, ticker, label or "Diluted",
      ytd_rows=last_ytd_rows
    )
    for r in rows:
      r.pop("_filed_dt", None)
    rows.sort(key=lambda r: r["PeriodEnd"], reverse=True)
    if last_q4_computes:
      bits = [
        c["end"] + "=" + str(c["val"]) + " (" + c["kind"] + ")"
        for c in last_q4_computes
      ]
      _ladder_step(
        "filings", "FY-(Q1+Q2+Q3) / FY-9mo",
        _filled_status(len(last_q4_computes)), "; ".join(bits),
      )
      _log_q4_computes(ticker)
    elif missing_before_compute:
      _ladder_step(
        "filings", "FY-(Q1+Q2+Q3) / FY-9mo", "no fill",
        ", ".join(missing_before_compute),
      )
    else:
      _ladder_step(
        "filings", "FY-(Q1+Q2+Q3) / FY-9mo", "not needed",
        "no missing quarters left",
      )
    missing = _still_missing_quarters(rows)
    if missing:
      _say(
        ticker,
        _missing_after_line("FY-(Q1+Q2+Q3) / FY-9mo", missing),
      )
  elif did_filings:
    _ladder_step(
      "filings", "FY-(Q1+Q2+Q3) / FY-9mo", "no fill",
      "no quarters to fill",
    )
  if rows:
    _emit_q4_warnings()
  return rows, method, tag, label, attempts


# =============================================================================
# WRITE CSV
# =============================================================================
def write_csv(rows, ticker):
  out_path = Path(sec_out_dir) / f"{ticker}_sec_eps_quarterly.csv"
  fieldnames = [
    "PeriodStart", "PeriodEnd", "EPS_GAAP", "Year", "Quarter",
    "EPS_Concept", "Source", "Form", "Filed",
    "AccessionNumber", "Unit",
  ]
  with open(out_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
  logging.debug("[" + ticker + "] wrote " + str(len(rows)) + " rows -> " + str(out_path))
  return out_path


# =============================================================================
# MAIN
# =============================================================================
def _blank_line():
  for handler in logging.getLogger("").handlers:
    stream = getattr(handler, "stream", None)
    if stream is not None:
      stream.write("\n")
      stream.flush()


def main():
  ticker_cik = load_ticker_cik_map()

  i = 1
  n_ok = 0
  n_skip = 0
  for ticker_raw in ticker_list:
    ticker = str(ticker_raw).replace(" ", "").upper()
    if not ticker:
      continue

    i_str = f"{i:<3}"
    i += 1
    logging.info(f"Iteration {i_str} : {ticker}")
    try:
      cik = ticker_cik.get(ticker)
      if cik is None:
        logging.warning(
          f"{ticker:<6}  SKIP  not in SEC ticker->CIK map"
        )
        n_skip += 1
        continue
      logging.debug("[" + ticker + "] CIK=" + f"{cik:010d}")

      try:
        rows, method, tag, label, attempts = resolve_eps(cik, ticker)
      except Exception as e:
        logging.warning(
          f"{ticker:<6}  SKIP  fetch failed: {e}"
        )
        logging.debug("[" + ticker + "] fetch exception", exc_info=True)
        n_skip += 1
        continue

      if not rows:
        logging.error(
          f"{ticker:<6}  ERROR  no quarterly EPS "
          f"(tried {', '.join(attempts)})"
        )
        _log_ladder(ticker, ["no quarters at all"])
        n_skip += 1
        continue

      still_missing = _still_missing_quarters(rows)
      rows = insert_blank_missing_quarters(rows, ticker)
      earliest = min(r["PeriodEnd"] for r in rows)
      latest = max(r["PeriodEnd"] for r in rows)
      out_path = write_csv(rows, ticker)
      n_ok += 1
      if still_missing:
        logging.error(
          ticker + "  Still missing EPS for quarter(s): "
          + ", ".join(still_missing)
        )
        logging.error(
          f"{ticker:<6}  INCOMPLETE  method={method}  "
          f"tag={tag}  rows={len(rows)}  {earliest}..{latest}  "
          f"-> {out_path.name}  missing=" + ",".join(still_missing)
        )
      else:
        logging.info(
          f"{ticker:<6}  OK    method={method}  "
          f"tag={tag}  rows={len(rows)}  {earliest}..{latest}  "
          f"-> {out_path.name}"
        )
      _log_ladder(ticker, still_missing)
      logging.debug(
        "[" + ticker + "] success method=" + str(method)
        + " tag=" + str(tag)
        + " concept=" + str(label)
        + " attempts=" + str(attempts)
      )
    finally:
      _blank_line()

  logging.info("All Done...  ok=" + str(n_ok) + "  skipped=" + str(n_skip))
  logging.info(
    "Ladder (merge missing dates): companyconcept JSON -> companyfacts "
    "JSON (other tags) -> 10-Q instance XBRL -> 8-K / 6-K HTML -> "
    "10-K / 20-F instance XBRL -> 10-K / 20-F HTML -> "
    "FY-(Q1+Q2+Q3) / FY-9mo (last resort)."
  )


if __name__ == "__main__":
  main()
