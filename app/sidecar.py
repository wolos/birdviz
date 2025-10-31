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
    """Main dashboard page with live updating list."""
    return """<!doctype html>
<meta charset='utf-8'>
<title>BirdNET Live</title>
<style>
body{font-family:system-ui,-apple-system,'Segoe UI',Roboto,Ubuntu,Arial;max-width:640px;margin:40px auto;padding:0 16px}
h1{font-size:20px;margin-bottom:10px}
ul{list-style:none;padding:0;margin:0}
li{border-bottom:1px solid #ddd;padding:8px 0}
.time{color:#666;font-size:13px}
.conf{float:right;color:#555}
</style>
<h1>BirdNET Live — Last 10 Unique Species</h1>
<ul id='list'><li>Loading…</li></ul>
<script>
const list=document.getElementById('list');
const MAX_ITEMS_JS=100;
const itemsBySci=new Map();
function liFor(d){
  const li=document.createElement('li');
  li.dataset.sci=(d.sci_name||'').toLowerCase();
  li.innerHTML=`<span class='name'>${d.display_name||'(unknown)'} </span>
     <span class='conf'>${(+d.confidence||0).toFixed(2)}</span>
     <div class='time'>${d.seen_local||''}</div>`;
  return li;
}
function renderUnique(arr){
  list.innerHTML='';
  itemsBySci.clear();
  for(const d of arr){
    const key=(d.sci_name||'').toLowerCase();
    if(!key||itemsBySci.has(key)) continue;
    const li=liFor(d);
    itemsBySci.set(key,li);
    list.appendChild(li);
  }
}
fetch('/recentunique?limit=10',{cache:'no-store'}).then(r=>r.json()).then(arr=>{renderUnique(arr);});
const es=new EventSource('/events');
es.addEventListener('append',e=>{
  try{
    const d=JSON.parse(e.data);
    const key=(d.sci_name||'').toLowerCase();
    if(!key)return;
    const li=liFor(d);
    if(itemsBySci.has(key)){
      const old=itemsBySci.get(key);
      if(old&&old.parentNode) old.parentNode.removeChild(old);
    }
    itemsBySci.set(key,li);
    list.prepend(li);
    while(list.children.length>MAX_ITEMS_JS){
      const last=list.lastElementChild;
      if(!last)break;
      const lastKey=(last.dataset.sci||'').toLowerCase();
      if(itemsBySci.get(lastKey)===last) itemsBySci.delete(lastKey);
      list.removeChild(last);
    }
  }catch(_){}
});
es.onerror=()=>{};
</script>"""


def main():
    _emit_if_new()
    threading.Thread(target=_poller, daemon=True).start()
    app.run(host='0.0.0.0', port=PORT, threaded=True)


if __name__ == "__main__":
    main()
