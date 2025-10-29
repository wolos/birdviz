from flask import Flask, request, jsonify
import sqlite3, os, time

DB_PATH = os.environ.get("BIRDS_DB", "/home/birdnet/BirdNET-Pi/scripts/birds.db")
app = Flask(__name__)

def rows(sql, args=()):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.execute(sql, args)
    out = [dict(r) for r in cur.fetchall()]
    con.close()
    return out

def detect_schema():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    tables = [r["name"] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    candidates = []
    # Known possibilities (table, ts, common, scientific, confidence)
    candidates += [
        ("detections", "datetime", "common_name", "scientific_name", "confidence"),
        ("detection", "datetime", "common_name", "scientific_name", "confidence"),
        ("predictions", "timestamp", "common_name", "scientific_name", "confidence"),
        ("events", "time", "species_common_name", "species_sci_name", "confidence"),
    ]
    chosen = None
    for t, ts, cn, sn, cf in candidates:
        if t in tables:
            cols = {r["name"] for r in con.execute(f"PRAGMA table_info({t})")}
            if ts in cols and cn in cols:
                chosen = (t, ts, cn, sn if sn in cols else None, cf if cf in cols else None)
                break
    if not chosen:
        for t in tables:
            cols = [r["name"] for r in con.execute(f"PRAGMA table_info({t})")]
            if any("common" in c for c in cols):
                ts = next((c for c in cols if "time" in c or "date" in c), cols[0])
                cn = next((c for c in cols if "common" in c), cols[0])
                sn = next((c for c in cols if "scient" in c), None)
                cf = next((c for c in cols if "conf" in c), None)
                chosen = (t, ts, cn, sn, cf)
                break
    con.close()
    return chosen

SCHEMA = detect_schema()

@app.get("/api/health")
def health():
    ok = SCHEMA is not None
    return jsonify({"ok": ok, "schema": SCHEMA, "time": int(time.time())}), (200 if ok else 500)

@app.get("/api/latest")
def latest():
    if not SCHEMA:
        return jsonify({"error":"schema not detected"}), 500
    limit = int(request.args.get("limit", 50))
    t, ts, cn, sn, cf = SCHEMA
    select_cols = [ts + " AS ts", f"{cn} AS common_name"]
    select_cols.append(f"{sn} AS scientific_name" if sn else "NULL AS scientific_name")
    select_cols.append(f"{cf} AS confidence" if cf else "NULL AS confidence")
    sql = f"SELECT {', '.join(select_cols)} FROM {t} ORDER BY {ts} DESC LIMIT ?"
    return jsonify(rows(sql, (limit,)))

@app.get("/api/latest_distinct")
def latest_distinct():
    if not SCHEMA:
        return jsonify({"error":"schema not detected"}), 500
    limit = int(request.args.get("limit", 10))
    t, ts, cn, sn, cf = SCHEMA
    window = max(limit * 6, 60)
    select_cols = [ts + " AS ts", f"{cn} AS common_name"]
    select_cols.append(f"{sn} AS scientific_name" if sn else "NULL AS scientific_name")
    select_cols.append(f"{cf} AS confidence" if cf else "NULL AS confidence")
    sql = f"SELECT {', '.join(select_cols)} FROM {t} ORDER BY {ts} DESC LIMIT ?"
    rs = rows(sql, (window,))
    seen = set()
    out = []
    for r in rs:
        key = (r.get("common_name") or "").strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(r)
        if len(out) >= limit:
            break
    return jsonify(out)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8756)
