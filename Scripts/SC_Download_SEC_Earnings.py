# ##############################################################################
# Download SEC XBRL GAAP diluted EPS (quarterly) for each ticker in
# Tracklist.csv. For each ticker, writes a separate CSV.
#
# NOTE: Adjusted / non-GAAP EPS is NOT a standard XBRL concept and is not
# reliably available as structured SEC data. For adjusted EPS use the CNBC
# scraper output (epsAdjActualValue) - see SC_CNBC_Earnings_Quarterly.py.
#
# Two ladders (stdout labels them "primary" vs "gap-fill"):
#   Primary — stop at the first method that returns any ~90-day quarters:
#     1. companyconcept JSON  EarningsPerShareDiluted, then Basic
#        (HTTP 200 with an empty units dict counts as a miss, e.g. INCY)
#     2. companyfacts JSON    same tags, then continuing-ops (e.g. LFST)
#     3. 10-Q and 10-K instance XBRL for the whole ticker (e.g. FOUR)
#   Gap-fill — leftover missing quarter-ends after JSON (and after primary
#   instance XBRL if JSON produced nothing):
#     4. 8-K HTML earnings release (Exhibit 99.1), e.g. HNGE Q4'25 = 0.37;
#        also INCY "GAAP diluted EPS", XNCR "net loss per share (diluted)",
#        FOUR image-letter hidden text / GAAP DILUTED EPS recon row,
#        GMED bullets ("GAAP diluted EPS was $0.14", "Diluted EPS for the
#        fourth quarter was $0.14") and income-statement Diluted row
#        under Three Months Ended. FY-end 8-Ks almost always have GAAP /
#        diluted EPS; wording varies, parser accepts several formats.
#     5. 10-Q and 10-K instance XBRL for those dates
#        (forms 10-Q, 10-Q/A, 10-K, 10-K/A — not 10-Q only)
#     6. compute Q4 as FY-(Q1+Q2+Q3) then FY-9mo (after 8-K, not before)
#     7. 10-K HTML "Quarterly Financial Data" table (e.g. DGII FY 2009)
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
_filings_cache = {}
_8k_cache = {}
_submissions_data_cache = {}

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
  "Primary: companyconcept JSON -> companyfacts JSON -> 10-Q and 10-K "
  "instance XBRL (stop at first hit). Gap-fill missing quarters: 8-K HTML, "
  "then 10-Q and 10-K instance XBRL, then FY-Q1-Q2-Q3 / FY-9mo, then 10-K HTML."
)
logging.debug("Ticker list: " + str(ticker_list))

Path(sec_out_dir).mkdir(parents=True, exist_ok=True)


# Tag search order. companyconcept only uses the first two; companyfacts and
# 10-Q / 10-K instance XBRL use the full list.
INSTANCE_XBRL_LADDER = "10-Q and 10-K instance XBRL"
EPS_TAG_PRIORITY = [
  ("EarningsPerShareDiluted", "Diluted"),
  ("EarningsPerShareBasic", "Basic"),
  ("EarningsPerShareBasicAndDiluted", "BasicAndDiluted"),
  ("IncomeLossFromContinuingOperationsPerDilutedShare", "ContinuingOpsDiluted"),
  ("IncomeLossFromContinuingOperationsPerBasicShare", "ContinuingOpsBasic"),
  ("IncomeLossFromContinuingOperationsPerBasicAndDilutedShare", "ContinuingOpsBasicAndDiluted"),
]
COMPANYCONCEPT_TAGS = EPS_TAG_PRIORITY[:2]


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


def _rows_from_facts(facts_json, ticker, concept_label):
  usable = _usable_units(facts_json)
  if not usable:
    logging.debug("[" + ticker + "] no usable unit lists: " + _facts_shape(facts_json))
    return []
  wrapped = dict(facts_json)
  wrapped["units"] = usable
  return extract_quarterly_rows(wrapped, ticker, concept_label)


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
def try_companyfacts(cik, ticker):
  global last_json_method
  last_json_method = "companyfacts"
  logging.debug("[" + ticker + "] method=companyfacts")
  url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
  resp = _http_get(url, ticker, "companyfacts")
  if resp.status_code == 404:
    logging.debug("[" + ticker + "] companyfacts 404")
    return None, None, None, None
  resp.raise_for_status()
  data = resp.json()
  gaap = (data.get("facts") or {}).get("us-gaap") or {}
  logging.debug(
    "[" + ticker + "] companyfacts entity=" + str(data.get("entityName"))
    + " us-gaap tags=" + str(len(gaap))
  )
  present = [tag for tag, _ in EPS_TAG_PRIORITY if tag in gaap]
  logging.debug("[" + ticker + "] companyfacts EPS-like tags present: " + str(present))

  for tag, label in EPS_TAG_PRIORITY:
    node = gaap.get(tag)
    if not node:
      logging.debug("[" + ticker + "] companyfacts missing tag " + tag)
      continue
    facts_json = {
      "entityName": data.get("entityName"),
      "tag": tag,
      "units": node.get("units") or {},
    }
    logging.debug("[" + ticker + "] companyfacts " + tag + " payload: " + _facts_shape(facts_json))
    rows = _rows_from_facts(facts_json, ticker, label)
    if rows:
      return rows, "companyfacts", tag, label
    logging.debug("[" + ticker + "] companyfacts " + tag + " had no quarterly rows")
  return None, None, None, None


# =============================================================================
# 3. 10-Q / 10-K INSTANCE XBRL
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


def _filings_from_recent(recent, allowed_forms=None):
  if allowed_forms is None:
    allowed_forms = ("10-Q", "10-K", "10-Q/A", "10-K/A")
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
  """Stdout bit like '10-K x4, 10-K/A x2, 10-Q x6'."""
  counts = {}
  for f in filings:
    form = str(f.get("form") or "?")
    counts[form] = counts.get(form, 0) + 1
  order = ("10-K", "10-K/A", "10-Q", "10-Q/A")
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
  logging.debug("[" + ticker + "] submissions 10-Q/K total=" + str(len(uniq)))
  _filings_cache[cik] = uniq
  return uniq


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
    allowed_forms=("8-K", "8-K/A"),
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
  logging.debug("[" + ticker + "] submissions 8-K total=" + str(len(uniq)))
  _8k_cache[cik] = uniq
  return uniq


def _select_8k_for_ends(filings, missing_ends):
  """For each missing quarter-end, keep up to two 8-Ks filed 0-100 days later.

  Prefer Item 2.02 (earnings) and the soonest filing after the period end so a
  long missing list cannot push the relevant earnings 8-K past _8K_MAX_FILINGS.
  """
  selected = []
  seen = set()
  for pe in missing_ends:
    try:
      end_d = parse_iso(pe)
    except Exception:
      continue
    cands = []
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
      if 0 <= delta <= 100:
        earnings = 1 if "2.02" in str(f.get("items") or "") else 0
        cands.append((earnings, -delta, f))
    cands.sort(key=lambda x: (x[0], x[1]), reverse=True)
    for _, _, f in cands[:2]:
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
  """Pick Exhibit 99.1 HTML. Names like incy-q42025xexx991.htm (Workiva)."""
  htmls = [n for n in names if n and n.lower().endswith((".htm", ".html"))]
  compact_hit = re.compile(r"x?exx?991|exhibit991|ex99d1")
  for n in htmls:
    nl = n.lower().replace("_", "").replace("-", "").replace(".", "")
    if compact_hit.search(nl):
      return n
  for n in htmls:
    nl = n.lower()
    if "99.1" in nl or "99_1" in nl or "ex99" in nl:
      return n
  return None


def _select_gapfill_filings(filings, missing_ends):
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
      if form.startswith("10-K"):
        delta = (rd_d - fy_end).days
        # same 10-K, later 10-K in the same FY (~90 days after Q3),
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
    "[" + ticker + "] parsed " + str(parsed_ok) + " 10-Q/K instances"
    + " no_xml=" + str(no_xml)
  )
  return by_tag, parsed_ok, no_xml


def try_xbrl_filings(cik, ticker):
  global last_json_method
  last_json_method = "10-Q and 10-K instance XBRL"
  logging.debug("[" + ticker + "] method=xbrl-10q")
  url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
  resp = _http_get(url, ticker, "submissions")
  if resp.status_code == 404:
    logging.debug("[" + ticker + "] submissions 404")
    return None, None, None, None
  resp.raise_for_status()
  filings = _recent_financial_filings(resp.json())
  logging.debug("[" + ticker + "] submissions 10-Q/K count used=" + str(len(filings)))
  if not filings:
    return None, None, None, None

  by_tag, parsed_ok, _no_xml = _eps_entries_from_filings(cik, ticker, filings)
  logging.debug("[" + ticker + "] parsed " + str(parsed_ok) + " 10-Q/K instances")

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
    rows = _rows_from_facts(facts_json, ticker, label)
    if rows:
      return rows, "xbrl-10q/" + class_label, tag, label
    logging.debug("[" + ticker + "] xbrl-10q " + tag + " had no quarterly rows")
  return None, None, None, None


def resolve_eps(cik, ticker):
  """Primary ladder: companyconcept -> companyfacts -> instance XBRL (first hit wins).

  Gap-fill of leftover missing quarters happens in _finalize_rows.
  """
  last_ladder.clear()
  attempts = []

  logging.info(ticker + "  primary: trying companyconcept")
  rows, method, tag, label = try_companyconcept(cik, ticker)
  attempts.append("companyconcept")
  if rows:
    _ladder_step(
      "primary", "companyconcept JSON", "hit", _ladder_hit_detail(rows)
    )
    _ladder_step(
      "primary", "companyfacts JSON", "skipped", "stop at first primary hit"
    )
    _ladder_step(
      "primary", INSTANCE_XBRL_LADDER, "skipped",
      "stop at first primary hit",
    )
    _log_json_success(ticker, method, tag, rows)
    return _finalize_rows(cik, ticker, rows, method, tag, label, attempts)
  logging.info(ticker + "  primary: companyconcept had no quarterly EPS")
  _ladder_step(
    "primary", "companyconcept JSON", "miss", "no quarterly EPS"
  )

  logging.info(ticker + "  primary: trying companyfacts")
  rows, method, tag, label = try_companyfacts(cik, ticker)
  attempts.append("companyfacts")
  if rows:
    _ladder_step(
      "primary", "companyfacts JSON", "hit", _ladder_hit_detail(rows)
    )
    _ladder_step(
      "primary", INSTANCE_XBRL_LADDER, "skipped",
      "stop at first primary hit",
    )
    _log_json_success(ticker, method, tag, rows)
    return _finalize_rows(cik, ticker, rows, method, tag, label, attempts)
  logging.info(ticker + "  primary: companyfacts had no quarterly EPS")
  _ladder_step(
    "primary", "companyfacts JSON", "miss", "no quarterly EPS"
  )

  logging.info(ticker + "  primary: trying 10-Q and 10-K instance XBRL")
  rows, method, tag, label = try_xbrl_filings(cik, ticker)
  attempts.append("10-Q and 10-K XBRL")
  if rows:
    _ladder_step(
      "primary", INSTANCE_XBRL_LADDER, "hit", _ladder_hit_detail(rows)
    )
    _log_json_success(ticker, method, tag, rows)
    return _finalize_rows(cik, ticker, rows, method, tag, label, attempts)
  logging.info(
    ticker + "  primary: 10-Q and 10-K instance XBRL had no quarterly EPS"
  )
  _ladder_step(
    "primary", INSTANCE_XBRL_LADDER, "miss", "no quarterly EPS"
  )

  return None, None, None, None, attempts


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


def _next_calendar_quarter_end(d):
  q = (d.month - 1) // 3
  if q == 3:
    y, m = d.year + 1, 3
  else:
    y, m = d.year, (q + 2) * 3
  return date(y, m, calendar.monthrange(y, m)[1])


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
  cur = _next_calendar_quarter_end(ends[0])
  last = ends[-1]
  while cur < last - timedelta(days=15):
    if not covered(cur):
      missing.append(cur.isoformat())
    cur = _next_calendar_quarter_end(cur)
  return missing


def _quarter_start(end_d):
  month = ((end_d.month - 1) // 3) * 3 + 1
  return date(end_d.year, month, 1)


def _placeholder_eps_row(ticker, pe_iso):
  """Keep the quarter on the CSV timeline with EPS_GAAP (col C) blank."""
  end_d = parse_iso(pe_iso)
  return {
    "Ticker": ticker,
    "Year": end_d.year,
    "Quarter": (end_d.month - 1) // 3 + 1,
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
  """Insert a row for every interior missing quarter-end; leave EPS_GAAP empty."""
  missing = _interior_missing_quarter_ends(rows)
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
  logging.info(
    ticker + "  blank EPS_GAAP for missing quarter(s): " + ", ".join(missing)
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
  """Untagged Q4s, FY-compute skips, plus holes in the quarterly series."""
  missing = []
  seen = set()
  for pe in (
    list(last_q4_cannot_ends)
    + _untagged_fy_q4_ends(rows)
    + _interior_missing_quarter_ends(rows)
  ):
    if pe in seen:
      continue
    seen.add(pe)
    missing.append(pe)
  missing.sort()
  return missing


def _sort_key(r):
  """Prefer earliest-filed; among ties, prefer non-amendment forms."""
  form = r["Form"] or ""
  is_amendment = form.endswith("/A")
  return (r["_filed_dt"] or date.max, 1 if is_amendment else 0)


def _make_row(ticker, unit_key, e, source, concept_label):
  end_dt = parse_iso(e["end"])
  return {
    "Ticker": ticker,
    "Year": end_dt.year,
    "Quarter": (end_dt.month - 1) // 3 + 1,
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


def _ladder_step(group, name, status, detail=""):
  last_ladder.append((group, name, status, detail))


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


def _log_ladder(ticker, leftover=None):
  """Stdout + log: the rungs actually taken for this ticker."""
  logging.info(ticker + "  ladder followed:")
  prev = None
  n = 0
  for group, name, status, detail in last_ladder:
    if group != prev:
      logging.info(ticker + "    " + group + ":")
      prev = group
    n += 1
    extra = " (" + detail + ")" if detail else ""
    logging.info(
      ticker + "      " + str(n) + ". " + name + " -> " + status + extra
    )
  if leftover:
    bang = "*" * 26
    logging.error(
      bang + "  " + ticker + "  leftover missing: "
      + ", ".join(leftover) + "  " + bang
    )
  elif last_ladder:
    logging.info(ticker + "    leftover missing: none")


def _make_q4_row(ticker, fy, q4_start, q4_end_iso, q4_val, concept_label, source):
  fy_end = parse_iso(fy["PeriodEnd"])
  return {
    "Ticker": ticker,
    "Year": fy_end.year,
    "Quarter": (fy_end.month - 1) // 3 + 1,
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
  """PeriodEnd=value (Form filed YYYY-MM-DD) for gap-fill stdout."""
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
    method = "HTML(10-K quarterly)"
  elif src.startswith("XBRL(10-Q/K)"):
    method = "10-Q and 10-K instance XBRL"
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
  """Print each Q4 we just computed, with the FY / quarter / 9-month sources."""
  for c in last_q4_computes:
    fy = c["fy"]
    fy_bit = (
      "FY " + fy["PeriodEnd"] + "=" + str(fy["EPS_GAAP"])
      + " (" + _fact_origin(fy) + ")"
    )
    if c["kind"] == "FY-9mo" and c.get("ytd") is not None:
      y = c["ytd"]
      logging.info(
        ticker + "  computed " + c["end"] + "=" + str(c["val"])
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
      logging.info(
        ticker + "  computed " + c["end"] + "=" + str(c["val"])
        + " from " + fy_bit
        + " minus Q1+Q2+Q3: " + "; ".join(q_bits)
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
    return "10-Q and 10-K instance XBRL"
  return m or "primary"


def _log_json_success(ticker, method, tag, rows):
  src = _primary_source_label(method)
  tagged = [r for r in rows if r.get("Source") == "XBRL"]
  if tagged:
    ends = [r["PeriodEnd"] for r in tagged]
    logging.info(
      ticker + "  primary: " + src + " produced "
      + str(len(tagged)) + " ~90-day EPS quarters"
      + " (tag=" + str(tag) + ") "
      + min(ends) + ".." + max(ends)
    )
  else:
    logging.info(
      ticker + "  primary: " + src
      + " returned no ~90-day EPS quarters (tag=" + str(tag) + ")"
    )
  if method == "companyconcept":
    logging.info(
      ticker + "  primary: not trying companyfacts or 10-Q and 10-K "
      "instance XBRL (companyconcept already produced quarters)"
    )
  elif method == "companyfacts":
    logging.info(
      ticker + "  primary: not trying 10-Q and 10-K instance XBRL "
      "(companyfacts already produced quarters)"
    )
  elif str(method).startswith("xbrl"):
    logging.info(
      ticker + "  primary: 10-Q and 10-K instance XBRL produced the series "
      "(companyconcept and companyfacts had none)"
    )
  missing_after_primary = _still_missing_quarters(rows)
  if missing_after_primary:
    logging.info(
      ticker + "  missing 3-month quarters after " + src
      + " (gap-fill still to run): "
      + ", ".join(missing_after_primary)
    )


def extract_quarterly_rows(facts_json, ticker, concept_label):
  """Return tagged ~90-day EPS rows. Do not compute Q4 here.

  Untagged Q4s are filled later in _finalize_rows: 8-K HTML first, then
  instance XBRL, then FY-(Q1+Q2+Q3) / FY-9mo, then 10-K HTML. Computing
  Q4 from FY before 8-K is wrong after an IPO share-count change (HNGE).
  """
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
  last_annual_rows.extend(annual)
  last_ytd_rows.extend(ytd)

  # Do not compute Q4 here. 8-K HTML (e.g. HNGE Q4'25 = 0.37) must run
  # before FY-(Q1+Q2+Q3), which can be wrong after an IPO share-count change.
  for r in quarterly:
    r.pop("_filed_dt", None)

  quarterly.sort(key=lambda r: r["PeriodEnd"], reverse=True)
  return quarterly


def fill_missing_q4_from_xbrl(cik, ticker, rows, missing_ends, concept_label):
  """Try 10-Q and 10-K instance XBRL for leftover missing quarter-ends.

  Looks at forms 10-Q, 10-Q/A, 10-K, and 10-K/A (not 10-Q only).
  Returns (rows, filled, note) where note is the stdout/ladder detail.
  """
  if not missing_ends:
    return rows, False, ""
  logging.info(
    ticker + "  gap-fill: trying 10-Q and 10-K instance XBRL for "
    + ", ".join(missing_ends)
  )
  filings = _load_financial_filings(cik, ticker)
  selected = _select_gapfill_filings(filings, missing_ends)
  tally = _form_tally(selected)
  logging.debug(
    "[" + ticker + "] gapfill selected=" + str(len(selected))
    + " reports=" + str([f.get("form") + ":" + str(f.get("report")) for f in selected])
  )
  if not selected:
    note = "no 10-Q or 10-K matched " + ", ".join(missing_ends)
    logging.info(ticker + "  gap-fill: " + note)
    return rows, False, note

  by_tag, parsed_ok, no_xml = _eps_entries_from_filings(cik, ticker, selected)
  if parsed_ok == 0:
    note = (
      "opened " + tally
      + "; parsed 0/" + str(len(selected))
      + " (no_xml=" + str(no_xml)
      + "); still missing " + ", ".join(missing_ends)
    )
    logging.info(
      ticker + "  gap-fill: 10-Q and 10-K instance XBRL -> " + note
    )
    return rows, False, note

  have = {r["PeriodEnd"] for r in rows}
  windows = [_fiscal_window(pe) for pe in missing_ends]
  added = []
  used_tag = None
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
      cand.append(_make_row(ticker, "USD/shares", e_copy, "XBRL(10-Q/K)", label))
    cand = _dedupe_by_period_end(cand)
    if cand:
      added = cand
      used_tag = tag + "/" + class_label
      for r in added:
        have.add(r["PeriodEnd"])
      break

  if not added:
    note = (
      "opened " + tally
      + "; parsed " + str(parsed_ok)
      + "; no 3-month EPS for " + ", ".join(missing_ends)
    )
    logging.info(
      ticker + "  gap-fill: 10-Q and 10-K instance XBRL -> " + note
    )
    return rows, False, note

  fill_bits = "; ".join(_filled_eps_bit(r) for r in added)
  note = fill_bits + " [opened " + tally + "]"
  logging.info(
    ticker + "  gap-fill: instance XBRL(" + str(used_tag) + ") filled "
    + str(len(added)) + " quarter(s): " + fill_bits
  )
  return rows + added, True, note


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
  if "gaap" in t and has_eps:
    return True
  return False


def _row_is_gaap_diluted(df, r):
  """True if this row is GAAP diluted EPS, including a child 'Diluted' row."""
  if _is_gaap_diluted_eps_label(df.iat[r, 0]):
    return True
  t = re.sub(r"[^a-z]+", " ", str(df.iat[r, 0]).lower()).strip()
  if t not in ("diluted", "diluted eps", "eps diluted"):
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
  """EPS in this cell, or in the next cell when this one is only '$'."""
  val = _parse_eps_cell(df.iat[r, c])
  if val is not None:
    return val
  s = str(df.iat[r, c]).strip()
  if s in ("$", "") or s.lower() == "nan":
    if c + 1 < df.shape[1]:
      return _parse_eps_cell(df.iat[r, c + 1])
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
  cl = str(cell).lower()
  if re.search(r"three\s+months\s+ended", cl):
    return "q"
  if re.search(r"\b(?:six|nine)\s+months\s+ended\b", cl):
    return "other"
  if re.search(r"\bquarter\s+ended\b", cl) and not re.search(r"\byear\s+ended\b", cl):
    return "q"
  if re.search(r"\byear\s+ended\b", cl):
    return "fy"
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
    kind = None
    md = None
    year = None
    for r in range(nhead):
      cell = str(df.iat[r, c])
      k = _header_period_kind(cell)
      if k and kind is None:
        kind = k
      elif k == "q":
        kind = "q"
      got = _month_day_from_cell(cell)
      if got:
        md = got
      y = _year_from_cell(cell)
      if y:
        year = y
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
  md = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}[q]
  return date(year, md[0], md[1])


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
  if re.search(r"\b(?:for the year|full year|year ended|annual)\b", near, re.I):
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
    r"(?P<vals>(?:\$\s*-?\d+\.\d+\s+)+)",
    text,
    re.I,
  )
  if m:
    heads = re.findall(r"(q[1-4]|fy)\s+(20\d{2})", m.group("heads"), re.I)
    vals = re.findall(r"\$\s*(-?\d+\.\d+)", m.group("vals"))
    for (kind, year_s), val_s in zip(heads, vals):
      if kind.lower() == "fy":
        continue
      found[_calendar_q_end(int(kind[1]), int(year_s)).isoformat()] = float(val_s)
  for m in re.finditer(
    r"\$\s*(-?\d+\.\d+)\s+gaap\s+diluted\s+eps\b", text, re.I
  ):
    if _span_has_non_gaap(text, m.start(), m.end()):
      continue
    window = text[max(0, m.start() - 400):m.start()]
    after = text[m.end():m.end() + 48]
    if _looks_like_annual_eps_window(window, after):
      continue
    end_d = _period_end_from_eps_window(window, default_end)
    _record_8k_eps(found, end_d, float(m.group(1)))
  for m in re.finditer(
    r"(?P<label>(?:gaap\s+)?(?:diluted\s+)?(?:gaap\s+)?"
    r"(?:earnings\s+per\s+share(?:\s*\([^)]{0,24}\))?|"
    r"eps|"
    r"earnings\s+per\s+diluted\s+share))"
    r"\s+(?:was|were|of|:)\s+\$\s*(?P<val>-?\d+\.\d+)",
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
    _record_8k_eps(found, end_d, float(m.group("val")))
  for m in re.finditer(
    r"diluted\s+(?:earnings\s+per\s+share|eps)\s+for\s+the\s+"
    r"(?:(?P<ord>first|1st|second|2nd|third|3rd|fourth|4th)\s+)?"
    r"quarter\s+was\s+\$\s*(?P<val>-?\d+\.\d+)",
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
    _record_8k_eps(found, end_d, float(m.group("val")))
  _keep_latest_year_for_duplicate_eps(found)
  return found


def _parse_8k_gaap_diluted_quarters(html):
  """Map period-end ISO -> GAAP diluted EPS from an earnings 8-K exhibit."""
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
        found[end_d.isoformat()] = val
  for end_iso, val in _parse_8k_gaap_diluted_from_text(html).items():
    found.setdefault(end_iso, val)
  return found


def fill_missing_from_8k(cik, ticker, rows, missing_ends, concept_label):
  """Fill missing quarters from Item 2.02 8-K earnings-release HTML."""
  if not missing_ends:
    return rows, False
  logging.info(
    ticker + "  gap-fill: trying 8-K HTML for "
    + ", ".join(missing_ends)
  )
  filings = _load_8k_filings(cik, ticker)
  selected = _select_8k_for_ends(filings, missing_ends)
  if not selected:
    logging.info(
      ticker + "  gap-fill: no 8-K filing in window for "
      + ", ".join(missing_ends)
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
      idx_resp = _http_get(index_url, ticker, "8-K index " + accn)
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
        ex_resp = _http_get(ex_url, ticker, "8-K exhibit " + ex_name)
        if ex_resp.status_code == 200:
          html = ex_resp.text
      if not html and filing.get("primary"):
        prim_url = (
          f"https://www.sec.gov/Archives/edgar/data/{cik_nolead}/"
          f"{accn_nodash}/{filing['primary']}"
        )
        prim_resp = _http_get(prim_url, ticker, "8-K primary")
        if prim_resp.status_code == 200:
          html = prim_resp.text
      if not html:
        continue
      parsed = _parse_8k_gaap_diluted_quarters(html)
    except Exception:
      logging.debug("[" + ticker + "] 8-K parse failed " + accn, exc_info=True)
      continue
    logging.debug(
      "[" + ticker + "] 8-K " + accn + " GAAP diluted quarters="
      + str(parsed)
    )
    for end_iso, val in parsed.items():
      if end_iso in have:
        continue
      try:
        end_d = parse_iso(end_iso)
      except Exception:
        continue
      matched = None
      for pe, want_d in want.items():
        if abs((end_d - want_d).days) <= 10:
          matched = pe
          break
      if not matched:
        continue
      added.append({
        "Ticker": ticker,
        "Year": end_d.year,
        "Quarter": (end_d.month - 1) // 3 + 1,
        "PeriodStart": _quarter_start_for_end(end_d).isoformat(),
        "PeriodEnd": end_iso,
        "EPS_GAAP": val,
        "EPS_Concept": concept_label or "Diluted",
        "Source": "HTML(8-K)",
        "Form": filing.get("form") or "8-K",
        "Filed": filing.get("filed"),
        "AccessionNumber": accn,
        "Unit": "USD/shares",
      })
      have.add(end_iso)

  if not added:
    logging.info(
      ticker + "  gap-fill: 8-K HTML had no GAAP diluted EPS for "
      + ", ".join(missing_ends)
    )
    return rows, False
  added.sort(key=lambda r: r["PeriodEnd"])
  logging.info(
    ticker + "  gap-fill: 8-K HTML filled "
    + str(len(added)) + " quarter(s): "
    + "; ".join(_filled_eps_bit(r) for r in added)
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
  if s.startswith("(") and s.endswith(")"):
    neg = True
    s = s[1:-1].strip()
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
  start_m = ((end_d.month - 1) // 3) * 3 + 1
  return date(end_d.year, start_m, 1)


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
    if not str(f.get("form") or "").startswith("10-K"):
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
  """Fill missing FY quarters from the 10-K HTML quarterly note."""
  if not missing_ends:
    return rows, False
  logging.info(
    ticker + "  gap-fill: trying 10-K HTML quarterly table for "
    + ", ".join(missing_ends)
  )
  filings = _load_financial_filings(cik, ticker)
  selected = _select_10k_for_ends(filings, missing_ends)
  if not selected:
    logging.info(
      ticker + "  gap-fill: no 10-K HTML filing matched "
      + ", ".join(missing_ends)
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
      resp = _http_get(html_url, ticker, "10-K HTML " + accn)
      if resp.status_code != 200 or not resp.text:
        continue
      rd = (filing.get("report") or "")[:10]
      fy_md = (parse_iso(rd).month, parse_iso(rd).day) if rd else (12, 31)
      parsed = _parse_10k_quarterly_tables(resp.text, fy_md)
    except Exception:
      logging.debug("[" + ticker + "] 10-K HTML parse failed " + accn, exc_info=True)
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
      added.append({
        "Ticker": ticker,
        "Year": item["end"].year,
        "Quarter": (item["end"].month - 1) // 3 + 1,
        "PeriodStart": item["start"].isoformat(),
        "PeriodEnd": end_iso,
        "EPS_GAAP": item["val"],
        "EPS_Concept": item["concept"],
        "Source": "HTML(10-K quarterly)",
        "Form": filing.get("form"),
        "Filed": filing.get("filed"),
        "AccessionNumber": accn,
        "Unit": "USD/shares",
      })
      have.add(end_iso)

  if not added:
    logging.info(
      ticker + "  gap-fill: HTML quarterly table had no EPS for "
      + ", ".join(missing_ends)
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
    logging.info(
      ticker + "  gap-fill: HTML filled requested "
      + "; ".join(_filled_eps_bit(r) for r in requested)
    )
  if extra:
    logging.info(
      ticker + "  gap-fill: HTML also filled "
      + str(len(extra)) + " nearby hole(s) from the same 10-K table: "
      + "; ".join(_filled_eps_bit(r) for r in extra)
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
    "HTML(8-K)",
    "Computed(FY-Q1-Q2-Q3)",
    "Computed(FY-9mo)",
    "HTML(10-K quarterly)",
  ]
  keys = [k for k in order if k in groups]
  keys += [k for k in groups if k not in order]
  json_method = str(method).split("+")[0]
  for src in keys:
    rs = sorted(groups[src], key=lambda x: x["PeriodEnd"])
    if src == "XBRL":
      ends = [r["PeriodEnd"] for r in rs]
      logging.info(
        ticker + "  from " + json_method + "/XBRL"
        + " tag=" + str(tag)
        + ": " + str(len(rs)) + " quarter(s) "
        + ends[0] + ".." + ends[-1]
      )
    else:
      bits = [r["PeriodEnd"] + "=" + str(r["EPS_GAAP"]) for r in rs]
      logging.info(ticker + "  from " + src + ": " + "; ".join(bits))


def _finalize_rows(cik, ticker, rows, method, tag, label, attempts):
  missing = _still_missing_quarters(rows) if rows else []
  did_gapfill = bool(rows and missing)
  if rows and not missing:
    logging.info(
      ticker + "  gap-fill: not needed (no missing quarters after primary)"
    )
    _ladder_step(
      "gap-fill", "8-K HTML", "not needed",
      "no missing quarters after primary",
    )
    _ladder_step(
      "gap-fill", INSTANCE_XBRL_LADDER, "not needed",
      "no missing quarters after primary",
    )
    _ladder_step(
      "gap-fill", "FY-(Q1+Q2+Q3) / FY-9mo", "not needed",
      "no missing quarters after primary",
    )
    _ladder_step(
      "gap-fill", "10-K HTML", "not needed",
      "no missing quarters after primary",
    )
  if rows and missing:
    rows, filled_8k = fill_missing_from_8k(
      cik, ticker, rows, missing, label
    )
    if filled_8k:
      method = method + "+8k"
      _ladder_step(
        "gap-fill", "8-K HTML", "filled",
        _ladder_source_bits(rows, "HTML(8-K)"),
      )
    else:
      _ladder_step(
        "gap-fill", "8-K HTML", "no fill", ", ".join(missing)
      )
    missing = _still_missing_quarters(rows)
    if missing:
      logging.info(
        ticker + "  still missing after gap-fill 8-K: "
        + ", ".join(missing)
      )
  if rows and missing:
    rows, filled, xbrl_note = fill_missing_q4_from_xbrl(
      cik, ticker, rows, missing, label
    )
    if filled:
      method = method + "+xbrl-gapfill"
      _ladder_step(
        "gap-fill", INSTANCE_XBRL_LADDER, "filled",
        xbrl_note or _ladder_source_bits(rows, "XBRL(10-Q/K)"),
      )
    else:
      _ladder_step(
        "gap-fill", INSTANCE_XBRL_LADDER, "no fill",
        xbrl_note or ", ".join(missing),
      )
    missing = _still_missing_quarters(rows)
    if missing:
      logging.info(
        ticker + "  still missing after gap-fill 10-Q and 10-K instance XBRL: "
        + ", ".join(missing)
      )
  elif did_gapfill:
    _ladder_step(
      "gap-fill", INSTANCE_XBRL_LADDER, "not needed",
      "no missing quarters left",
    )
  if rows:
    missing_before_compute = list(missing)
    rows = _apply_q4_from_fy(
      rows, last_annual_rows, ticker, label, ytd_rows=last_ytd_rows
    )
    for r in rows:
      r.pop("_filed_dt", None)
    rows.sort(key=lambda r: r["PeriodEnd"], reverse=True)
    if did_gapfill:
      if last_q4_computes:
        bits = [
          c["end"] + "=" + str(c["val"]) + " (" + c["kind"] + ")"
          for c in last_q4_computes
        ]
        _ladder_step(
          "gap-fill", "FY-(Q1+Q2+Q3) / FY-9mo", "filled", "; ".join(bits)
        )
      elif missing_before_compute:
        _ladder_step(
          "gap-fill", "FY-(Q1+Q2+Q3) / FY-9mo", "no fill",
          ", ".join(missing_before_compute),
        )
      else:
        _ladder_step(
          "gap-fill", "FY-(Q1+Q2+Q3) / FY-9mo", "not needed",
          "no missing quarters left",
        )
    if last_q4_computes:
      _log_q4_computes(ticker)
    missing = _still_missing_quarters(rows)
    if missing:
      logging.info(
        ticker + "  still missing after FY-(Q1+Q2+Q3) / FY-9mo: "
        + ", ".join(missing)
      )
  if rows and missing:
    rows, filled_html = fill_missing_q4_from_html(
      cik, ticker, rows, missing, label
    )
    if filled_html:
      method = method + "+html-10k"
      html_bits = _ladder_source_bits(rows, "HTML(10-K quarterly)")
      rows = _apply_q4_from_fy(
        rows, last_annual_rows, ticker, label, ytd_rows=last_ytd_rows
      )
      for r in rows:
        r.pop("_filed_dt", None)
      rows.sort(key=lambda r: r["PeriodEnd"], reverse=True)
      if last_q4_computes:
        html_bits += "; then computed " + "; ".join(
          c["end"] + "=" + str(c["val"]) + " (" + c["kind"] + ")"
          for c in last_q4_computes
        )
      _ladder_step("gap-fill", "10-K HTML", "filled", html_bits)
      _log_q4_computes(ticker)
      missing = _still_missing_quarters(rows)
      if missing:
        logging.info(
          ticker + "  still missing after gap-fill 10-K HTML: "
          + ", ".join(missing)
        )
    else:
      _ladder_step(
        "gap-fill", "10-K HTML", "no fill", ", ".join(missing)
      )
  elif did_gapfill:
    _ladder_step(
      "gap-fill", "10-K HTML", "not needed", "no missing quarters left"
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
        logging.warning(
          f"{ticker:<6}  SKIP  no quarterly EPS "
          f"(tried {', '.join(attempts)})"
        )
        _log_ladder(ticker)
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
          ticker + "  still missing EPS for quarter(s): "
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
    "Ladder: primary (stop at first hit) companyconcept JSON -> "
    "companyfacts JSON -> 10-Q and 10-K instance XBRL. Then gap-fill missing "
    "quarters: 8-K HTML -> 10-Q and 10-K instance XBRL -> "
    "FY-(Q1+Q2+Q3) / FY-9mo -> 10-K HTML."
  )


if __name__ == "__main__":
  main()
