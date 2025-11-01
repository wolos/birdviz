#!/usr/bin/env python3
# BirdNET-Pi Sidecar: Unique Species Live API + Dashboard

import os
import json
import time
import queue
import threading
import sqlite3
from flask import Flask, Response, jsonify, request

# --- Configuration ---
DB_PATH = os.path.expanduser('~/BirdNET-Pi/scripts/birds.db')
PORT = 8090
MAX_ITEMS = 100
KEEPALIVE_SECS = 15
POLL_INTERVAL = 0.5
WRITE_SETTLE = 0.15

app = Flask(__name__)
_update_q = queue.Queue(maxsize=400)
_recent = []
_last_key = None
_last_mtime = 0.0


def _connect_ro() -> sqlite3.Connection:
    uri = f"file:{DB_PATH}?mode=ro&cache=shared"
    return sqlite3.connect(uri, uri=True, check_same_thread=False)


def _fetch_last_from_db() -> dict | None:
    """Fetch the latest row from detections table."""
    con = _connect_ro()
    con.row_factory = sqlite3.Row
    try:
        sql = """
          WITH rows AS (
            SELECT
              (Date || ' ' || Time) AS seen_local,
              Com_Name AS display_name,
              Sci_Name AS sci_name,
              Confidence AS confidence,
              strftime('%s', Date || ' ' || Time) AS ts_epoch
            FROM detections
          )
          SELECT * FROM rows
          ORDER BY ts_epoch DESC
          LIMIT 1
        """
        row = con.execute(sql).fetchone()
        return dict(row) if row else None
    finally:
        con.close()


def _emit_if_new() -> None:
    """Check for a new detection and emit it to the SSE queue."""
    global _last_key
    row = _fetch_last_from_db()
    if not row:
        return
    key = f"{row.get('ts_epoch')}|{row.get('sci_name') or row.get('display_name')}"
    if key != _last_key:
        _last_key = key
        entry = {
            "seen_local": row.get("seen_local"),
            "display_name": row.get("display_name") or (row.get("sci_name") or "").title() or "Unknown bird",
            "confidence": row.get("confidence"),
            "sci_name": row.get("sci_name") or ""
        }
        _recent.insert(0, entry)
        del _recent[MAX_ITEMS:]
        try:
            _update_q.put_nowait(json.dumps(entry))
        except queue.Full:
            pass


def _poller() -> None:
    """Poll the BirdNET-Pi database file for changes."""
    global _last_mtime
    next_ka = time.time() + KEEPALIVE_SECS
    while True:
        try:
            mtime = os.path.getmtime(DB_PATH)
            if mtime != _last_mtime:
                _last_mtime = mtime
                time.sleep(WRITE_SETTLE)
                _emit_if_new()
        except FileNotFoundError:
            pass

        now = time.time()
        if now >= next_ka:
            try:
                _update_q.put_nowait("__KEEPALIVE__")
            except queue.Full:
                pass
            next_ka = now + KEEPALIVE_SECS

        time.sleep(POLL_INTERVAL)


@app.after_request
def _no_cache(resp):
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@app.get("/last")
def last():
    if not _recent:
        _emit_if_new()
    return jsonify(_recent[0] if _recent else {})


@app.get("/recentunique")
def recentunique():
    """Return last N unique species (by Sci_Name), newest to oldest."""
    try:
        limit = int(request.args.get("limit", "10"))
    except Exception:
        limit = 10

    con = _connect_ro()
    con.row_factory = sqlite3.Row
    try:
        sql = """
          WITH rows AS (
            SELECT
              (Date || ' ' || Time) AS seen_local,
              Com_Name AS display_name,
              Sci_Name AS sci_name,
              Confidence AS confidence,
              strftime('%s', Date || ' ' || Time) AS ts_epoch
            FROM detections
          ),
          latest AS (
            SELECT sci_name, MAX(ts_epoch) AS max_ts
            FROM rows
            GROUP BY sci_name
          )
          SELECT r.seen_local, r.display_name, r.sci_name, r.confidence, r.ts_epoch
          FROM rows r
          JOIN latest l ON r.sci_name = l.sci_name AND r.ts_epoch = l.max_ts
          ORDER BY r.ts_epoch DESC
          LIMIT ?
        """
        rows = [dict(r) for r in con.execute(sql, (limit,))]
        for r in rows:
            if not (isinstance(r.get("display_name"), str) and r["display_name"].strip()):
                sci = (r.get("sci_name") or "").strip()
                r["display_name"] = sci.title() if sci else "Unknown bird"
        return jsonify(rows)
    finally:
        con.close()


@app.get("/events")
def events():
    """Server-Sent Events stream for live updates."""
    def gen():
        yield "event: snapshot\ndata: " + json.dumps(_recent) + "\n\n"
        while True:
            msg = _update_q.get()
            if msg == "__KEEPALIVE__":
                yield ": keepalive\n\n"
            else:
                yield "event: append\ndata: " + msg + "\n\n"

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return Response(gen(), headers=headers)


@app.get("/debug")
def debug():
    last_row = _recent[0] if _recent else None
    return jsonify({
        "db_path": DB_PATH,
        "port": PORT,
        "max_items": MAX_ITEMS,
        "poll_interval": POLL_INTERVAL,
        "keepalive_secs": KEEPALIVE_SECS,
        "last_row": last_row
    })


@app.get("/")
def index():
    """Main dashboard page with live updating list (clean style)."""
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>BirdNET — Clean</title>

  <!-- Roboto Flex (variable weight) -->
  <link href="https://fonts.googleapis.com/css2?family=Roboto+Flex:opsz,wght@8..144,100..1000&display=swap" rel="stylesheet">

  <style>
    :root {
      --fs: 48px;                 /* computed at runtime to fit the longest name */
      --row-gap: 0.35em;
      --pad: clamp(12px, 4vw, 28px);
      --bg: #0c0f10;
      --fg: #e9eef2;
      --muted: #6d7b86;
      --maxw: 1200px;
    }
    html, body {
      height: 100%;
      margin: 0;
      background: var(--bg);
      color: var(--fg);
      font-family: "Roboto Flex", system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
      font-optical-sizing: auto;
    }
    .wrap {
      min-height: 100%;
      display: grid;
      place-items: center;
      padding: var(--pad);
    }
    .panel {
      width: min(95vw, var(--maxw));
      display: grid;
      align-content: start;
      gap: .5rem;
    }
    /* Pure list — no title/date/time/confidence anywhere */
    .list {
      list-style: none;
      padding: 0;
      margin: 0;
      display: grid;
      gap: var(--row-gap);
    }
    .item {
      line-height: 1.08;
      letter-spacing: 0.01em;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      font-size: var(--fs);       /* one size for all rows */
    }
    /* Subtle fade newest→oldest */
    .item[data-rank="0"] { color: var(--fg); }
    .item[data-rank="1"] { color: color-mix(in oklab, var(--fg) 92%, var(--muted)); }
    .item[data-rank="2"] { color: color-mix(in oklab, var(--fg) 86%, var(--muted)); }
    .item[data-rank="3"] { color: color-mix(in oklab, var(--fg) 80%, var(--muted)); }
    .item[data-rank="4"] { color: color-mix(in oklab, var(--fg) 74%, var(--muted)); }
    .item[data-rank="5"] { color: color-mix(in oklab, var(--fg) 68%, var(--muted)); }
    .item[data-rank="6"] { color: color-mix(in oklab, var(--fg) 62%, var(--muted)); }
    .item[data-rank="7"] { color: color-mix(in oklab, var(--fg) 56%, var(--muted)); }
    .item[data-rank="8"] { color: color-mix(in oklab, var(--fg) 50%, var(--muted)); }
    .item[data-rank="9"] { color: color-mix(in oklab, var(--fg) 44%, var(--muted)); }
    @media (max-width: 480px) { :root { --row-gap: 0.28em; } }
  </style>
</head>
<body>
  <div class="wrap">
    <main class="panel">
      <ul id="list" class="list" aria-label="Recent Bird Species"></ul>
    </main>
  </div>

  <script>
  const DATA_URL = "/recentunique?limit=10";
  const MAX_ITEMS = 10;

  // permissive JSON loader (works even if content-type is text/plain)
  async function loadJson(res){
    try { return await res.clone().json(); }
    catch(_) {
      try { return JSON.parse(await res.text()); }
      catch(_) { return null; }
    }
  }

  function transform(raw){
    if(!raw) return [];
    if(Array.isArray(raw) && typeof raw[0]==="string") return raw;
    if(Array.isArray(raw) && typeof raw[0]==="object"){
      const k = ["display_name","species","species_name","name","label"]
        .find(x => raw[0] && x in raw[0]);
      if(k) return raw.map(o => o[k]);
    }
    if(typeof raw==="object"){
      const arrKey = Object.keys(raw).find(k => Array.isArray(raw[k]));
      if(arrKey) return transform(raw[arrKey]);
    }
    return [];
  }

  function wght(i, total){
    if(total <= 1) return 1000;
    const hi = 1000, lo = 100;
    const t = i / (total - 1);  // 0=newest(top) .. 1=oldest(bottom)
    return Math.round(hi + (lo - hi) * t);
  }

  async function computeFontSizeToFill(containerEl, items){
    if(document.fonts && document.fonts.ready){ try{ await document.fonts.ready; }catch{} }
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    const refPx = 100;
    const width = containerEl.clientWidth || 1;
    let widest = 1;
    items.forEach(({text, weight}) => {
      ctx.font = `${weight} ${refPx}px "Roboto Flex", system-ui, sans-serif`;
      widest = Math.max(widest, ctx.measureText(text).width);
    });
    let fs = (width / widest) * refPx;
    return Math.max(18, Math.min(fs, 220));
  }

  function render(targetEl, items){
    targetEl.innerHTML = "";
    items.forEach((item, i) => {
      const li = document.createElement("li");
      li.className = "item";
      li.dataset.rank = String(i);
      li.style.fontVariationSettings = `"wght" ${item.weight}`;
      li.style.fontWeight = item.weight;   // some engines reflect to var axis
      li.textContent = item.text;
      targetEl.appendChild(li);
    });
  }

  function uniqueOrder(names){
    const seen = new Set(); const out = [];
    for(const n of names){
      if(!n || seen.has(n)) continue;
      seen.add(n); out.push(n);
      if(out.length >= MAX_ITEMS) break;
    }
    return out;
  }

  async function initialRender(listEl){
    const res = await fetch(DATA_URL, { cache: "no-store" });
    if(!res.ok) throw new Error("HTTP " + res.status);
    const raw = await loadJson(res);
    const names = transform(raw);
    const uniq = uniqueOrder(names);
    if(!uniq.length) return;
    const items = uniq.map((text, i, arr) => ({ text, weight: wght(i, arr.length) }));
    const fs = await computeFontSizeToFill(listEl, items);
    document.documentElement.style.setProperty("--fs", `${fs}px`);
    render(listEl, items);
  }

  function liveUpdates(listEl){
    const es = new EventSource("/events");
    es.addEventListener("append", async (e) => {
      try{
        const d = JSON.parse(e.data);
        const name = d.display_name || d.species || d.species_name || d.name || d.label || d.sci_name || "";
        if(!name) return;
        // build current list of names
        const current = Array.from(listEl.querySelectorAll(".item")).map(li => li.textContent);
        // move to top, dedupe, trim
        const next = [name, ...current.filter(n => n !== name)].slice(0, MAX_ITEMS);
        const items = next.map((text, i, arr) => ({ text, weight: wght(i, arr.length) }));
        const fs = await computeFontSizeToFill(listEl, items);
        document.documentElement.style.setProperty("--fs", `${fs}px`);
        render(listEl, items);
      }catch(_){}
    });
    es.onerror = () => {}; // keep silent
  }

  (async function init(){
    const listEl = document.getElementById("list");
    try {
      await initialRender(listEl);
      liveUpdates(listEl);
    } catch (e) {
      console.error(e); // page stays blank on error per your spec
    }
  })();
  </script>
</body>
</html>
"""


def main():
    _emit_if_new()
    threading.Thread(target=_poller, daemon=True).start()
    app.run(host='0.0.0.0', port=PORT, threaded=True)


if __name__ == "__main__":
    main()
