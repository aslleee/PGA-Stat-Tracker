# pip install requests
import json, re, csv
from typing import Any, Dict, List, Tuple, Optional
import requests
from pathlib import Path

BASE = "https://www.pgatour.com"
STATS_LANDING = f"{BASE}/stats"
LANG_PATH = "en"
STAT_ID = "120"  # ← your statId (driving distance page you clicked)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PGAStatScraper/1.2)",
    "Accept": "*/*",
    "x-nextjs-data": "1",
}
DEFAULT_COOKIES = {
    # Drop in consent cookies if needed
    # "OptanonConsent": "...",
    # "OTGPPConsent": "...",
}

# ===== BuildId discovery (stays stable across deployments) ===================
def get_build_id() -> str:
    r = requests.get(STATS_LANDING, headers=DEFAULT_HEADERS, cookies=DEFAULT_COOKIES, timeout=20)
    r.raise_for_status()
    html = r.text
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', html, re.S)
    if m:
        try:
            return json.loads(m.group(1))["buildId"]
        except Exception:
            pass
    m2 = re.search(r'"buildId"\s*:\s*"([^"]+)"', html)
    if not m2:
        raise RuntimeError("Could not find Next.js buildId from /stats")
    return m2.group(1)

def fetch_stat_detail_json(stat_id: str) -> Dict[str, Any]:
    url = f"{BASE}/_next/data/{get_build_id()}/{LANG_PATH}/stats/detail/{stat_id}.json"
    r = requests.get(url, headers=DEFAULT_HEADERS, cookies=DEFAULT_COOKIES, params={"statId": stat_id}, timeout=30)
    r.raise_for_status()
    return r.json()

# ===== Find which React Query contains the table =============================
def _looks_like_rows(arr: Any) -> bool:
    return isinstance(arr, list) and arr and isinstance(arr[0], dict)

def _extract_table_like(node: Any) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    rows, cols = [], []
    def scan(x: Any):
        nonlocal rows, cols
        if rows: return
        if isinstance(x, dict):
            for rk in ("rows", "data", "tableRows", "items"):
                if rk in x and _looks_like_rows(x[rk]):
                    rows = x[rk]
                    if "columns" in x and isinstance(x["columns"], list):
                        cols = [c for c in x["columns"] if isinstance(c, dict)]
                    return
            for v in x.values(): scan(v)
        elif isinstance(x, list):
            for v in x: scan(v)
    scan(node)
    return rows, cols

def locate_rows_columns(page_props: Dict[str, Any], stat_id: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    dehydrated = (page_props.get("dehydratedState") or {}).get("queries") or []
    best = None
    # Prefer the query whose key mentions our statId
    for q in dehydrated:
        key = q.get("queryKey")
        key_str = json.dumps(key, ensure_ascii=False)
        if stat_id in (key_str or ""):
            best = q
            break
    if best is None and dehydrated:
        best = dehydrated[0]

    if not best: return [], [], None
    data = (best.get("state") or {}).get("data")
    if not data: return [], [], best

    rows, cols = _extract_table_like(data)
    if rows: return rows, cols, best

    # Rare fallback
    rows, cols = _extract_table_like(page_props)
    return rows, cols, best

# ===== Normalization helpers ==================================================
def normalize_rows(rows: List[Dict[str, Any]], cols: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # likely keys
    player_fields = ["playerName", "player", "fullName", "name", "playerFullName"]
    rank_fields   = ["rank", "ranking", "position"]
    avg_candidates = {"avg", "average", "avg_distance", "average_distance", "avgdist", "AVG"}
    tot_candidates = {"total", "total_yards", "yards", "distance_total", "TOT"}
    att_candidates = {"attempts", "events", "rounds", "ATT", "EVT", "count"}

    # map column metadata → normalized names
    col_map = {}
    for c in cols:
        raw = (c.get("field") or c.get("id") or c.get("key") or c.get("name") or "").lower()
        if not raw: continue
        if any(a in raw for a in avg_candidates): col_map[c.get("field") or c.get("id") or raw] = "avg_distance"
        elif any(t in raw for t in tot_candidates): col_map[c.get("field") or c.get("id") or raw] = "total_yards"
        elif any(a in raw for a in att_candidates): col_map[c.get("field") or c.get("id") or raw] = "attempts_or_events"

    def pick_first(d, keys):
        for k in keys:
            if k in d and d[k] not in (None, ""):
                return d[k]
        return None

    out = []
    for r in rows:
        item = {"rank": pick_first(r, rank_fields), "player": pick_first(r, player_fields)}
        for k, v in r.items():
            tgt = col_map.get(k)
            if tgt: item[tgt] = v

        # fallback by raw keys
        lk = {k.lower(): k for k in r.keys()}
        if "avg_distance" not in item:
            for cand in avg_candidates:
                if cand in lk: item["avg_distance"] = r[lk[cand]]; break
        if "total_yards" not in item:
            for cand in tot_candidates:
                if cand in lk: item["total_yards"] = r[lk[cand]]; break
        if "attempts_or_events" not in item:
            for cand in att_candidates:
                if cand in lk: item["attempts_or_events"] = r[lk[cand]]; break

        if any(item.get(x) is not None for x in ("player","avg_distance","total_yards","rank")):
            out.append(item)
    return out

# ===== Pretty printers / full export =========================================
def preview_columns(cols: List[Dict[str, Any]]):
    if not cols:
        print("// No columns metadata found")
        return
    print("=== Columns Metadata (first 20) ===")
    for c in cols[:20]:
        print(json.dumps(c, ensure_ascii=False))
    if len(cols) > 20:
        print(f"... ({len(cols)-20} more columns)")
    print()

def preview_sample_row(rows: List[Dict[str, Any]]):
    if not rows:
        print("// No rows found")
        return
    print("=== Sample Row (raw) ===")
    print(json.dumps(rows[0], ensure_ascii=False, indent=2))
    print(f"(keys: {sorted(rows[0].keys())})\n")

def export_raw_and_normalized(rows: List[Dict[str, Any]], cols: List[Dict[str, Any]], stat_id: str):
    outdir = Path("out"); outdir.mkdir(exist_ok=True)
    raw_path = outdir / f"stat_{stat_id}_rows_raw.json"
    cols_path = outdir / f"stat_{stat_id}_columns.json"
    norm_path = outdir / f"stat_{stat_id}_normalized.json"
    csv_path = outdir / f"stat_{stat_id}_rows_raw.csv"

    # JSON exports
    raw_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    cols_path.write_text(json.dumps(cols, ensure_ascii=False, indent=2))

    normalized = normalize_rows(rows, cols)
    norm_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2))

    # CSV with union of all keys (so you see EVERYTHING each row offers)
    all_keys = set()
    for r in rows: all_keys.update(r.keys())
    headers = sorted(all_keys)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader(); w.writerows(rows)

    print(f"Saved:\n  {raw_path}\n  {cols_path}\n  {norm_path}\n  {csv_path}\n")

def main():
    blob = fetch_stat_detail_json(STAT_ID)
    page_props = blob.get("pageProps", {}) or {}

    rows, cols, q = locate_rows_columns(page_props, STAT_ID)
    if not rows:
        print("// Could not locate rows. Query keys present:")
        keys = [(qi.get("queryKey"), (qi.get('state') or {}).get('data') is not None) for qi in (page_props.get("dehydratedState") or {}).get("queries", [])]
        print(json.dumps(keys, ensure_ascii=False, indent=2))
        return

    # Show which query we matched (helps confirm you’re in the right payload)
    print("=== Matched Query ===")
    print(json.dumps(q.get("queryKey"), ensure_ascii=False, indent=2), "\n")

    # Show columns + one raw row so you can see ALL fields
    preview_columns(cols)
    preview_sample_row(rows)

    # Export everything (raw rows, columns, normalized rows, and a wide CSV)
    export_raw_and_normalized(rows, cols, STAT_ID)

    # Also print normalized JSON to stdout (what you were expecting earlier)
    normalized = normalize_rows(rows, cols)
    print("=== Normalized JSON (truncated to first 10) ===")
    print(json.dumps(normalized[:10], ensure_ascii=False, indent=2))
    if len(normalized) > 10:
        print(f"... ({len(normalized)-10} more rows)")

if __name__ == "__main__":
    main()
