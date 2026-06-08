"""PeriPage A40 HA add-on web server.

Serves a single-page upload UI behind Home Assistant ingress, probes printer
reachability, and prints uploaded PDFs via the peripage_a40 library over RFCOMM.
All Bluetooth access is serialized through a lock so concurrent requests never
hit the dongle at once.
"""
from __future__ import annotations

import os
import time
import tempfile
import threading

from flask import Flask, request, jsonify, Response
import peripage_a40 as ppa

MAC = os.environ.get("PRINTER_MAC", "04:7F:0E:B0:45:18")
CHANNEL = int(os.environ.get("RFCOMM_CHANNEL", "1"))
DITHER = os.environ.get("DITHER", "true").lower() in ("true", "1", "yes")
PORT = int(os.environ.get("PORT", "8099"))
PROBE_TIMEOUT = 4.0
STATUS_CACHE_TTL = 15.0  # don't hammer the dongle with connect probes

app = Flask(__name__)
_bt_lock = threading.Lock()
_printing = False
_status_cache = {"ts": 0.0, "state": "unknown"}


def _probe_once() -> str:
    t = ppa.RfcommTransport(MAC, channel=CHANNEL, connect_timeout=PROBE_TIMEOUT)
    try:
        t.connect()
        t.close()
        return "online"
    except ppa.PrinterAsleep:
        return "asleep"
    except Exception:
        return "error"


def _probe_state() -> str:
    """Connect/disconnect probe -> 'online' | 'asleep' | 'error'.

    Retries once on a transient error (e.g. the printer is briefly busy right
    after a print closed its connection); 'asleep' is definitive, no retry.
    """
    st = _probe_once()
    if st == "error":
        time.sleep(1.0)
        st = _probe_once()
    return st


def _status(force: bool = False) -> str:
    if _printing:
        return "printing"
    now = time.time()
    if not force and (now - _status_cache["ts"]) < STATUS_CACHE_TTL:
        return _status_cache["state"]
    with _bt_lock:
        if _printing:
            return "printing"
        state = _probe_state()
    _status_cache.update(ts=time.time(), state=state)
    return state


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PeriPage A40</title>
<style>
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body { font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
         margin: 0; padding: 1.25rem; max-width: 640px; }
  h1 { font-size: 1.25rem; margin: 0 0 1rem; }
  .card { border: 1px solid color-mix(in srgb, currentColor 18%, transparent);
          border-radius: 14px; padding: 1rem 1.1rem; margin-bottom: 1rem; }
  .status { display: flex; align-items: center; gap: .6rem; font-weight: 600; }
  .dot { width: 12px; height: 12px; border-radius: 50%; background: #9aa0a6; flex: none; }
  .dot.online { background: #1faa59; } .dot.asleep { background: #f5a623; }
  .dot.error  { background: #e0413e; } .dot.printing { background: #2d7ff9; animation: pulse 1s infinite; }
  @keyframes pulse { 50% { opacity: .35; } }
  .sub { font-weight: 400; opacity: .7; font-size: .85rem; margin-top: .35rem; }
  label.file { display: block; border: 1.5px dashed color-mix(in srgb, currentColor 30%, transparent);
               border-radius: 12px; padding: 1.4rem; text-align: center; cursor: pointer; }
  label.file:hover { border-color: #2d7ff9; }
  input[type=file] { display: none; }
  .fname { margin-top: .6rem; font-size: .9rem; opacity: .8; }
  button { font: inherit; font-weight: 600; border: 0; border-radius: 10px; padding: .7rem 1.2rem;
           background: #2d7ff9; color: #fff; cursor: pointer; width: 100%; }
  button:disabled { opacity: .5; cursor: default; }
  button.ghost { background: transparent; color: inherit;
                 border: 1px solid color-mix(in srgb, currentColor 25%, transparent); }
  .row { display: flex; gap: .6rem; margin-top: .8rem; }
  .msg { margin-top: .9rem; padding: .7rem .9rem; border-radius: 10px; font-size: .9rem; display: none; }
  .msg.ok  { display: block; background: color-mix(in srgb, #1faa59 18%, transparent); }
  .msg.warn{ display: block; background: color-mix(in srgb, #f5a623 22%, transparent); }
  .msg.err { display: block; background: color-mix(in srgb, #e0413e 18%, transparent); }
  .meta { font-size: .78rem; opacity: .6; margin-top: 1rem; }
</style>
</head>
<body>
  <h1>PeriPage A40</h1>

  <div class="card">
    <div class="status"><span id="dot" class="dot"></span><span id="statusText">Checking...</span></div>
    <div class="sub" id="statusSub"></div>
    <div class="row"><button class="ghost" id="refresh">Refresh status</button></div>
  </div>

  <div class="card">
    <label class="file" id="drop">
      <input type="file" id="file" accept="application/pdf">
      <div>Tap to choose a PDF</div>
      <div class="fname" id="fname">No file selected</div>
    </label>
    <div class="row"><button id="print" disabled>Print</button></div>
    <div class="msg" id="msg"></div>
  </div>

  <div class="meta" id="meta"></div>

<script>
const $ = (id) => document.getElementById(id);
let file = null;

function setStatus(state) {
  const map = {
    online:   ["Printer online",  "Ready to print."],
    asleep:   ["Asleep / off",    "Press the printer power or feed button to wake it."],
    printing: ["Printing...",     "A job is in progress."],
    error:    ["Bluetooth error", "Could not reach the adapter. Check the dongle and logs."],
    unknown:  ["Unknown",         ""],
  };
  const pair = map[state] || map.unknown;
  $("dot").className = "dot " + state;
  $("statusText").textContent = pair[0];
  $("statusSub").textContent = pair[1];
}

async function refresh(force) {
  setStatus("unknown"); $("statusText").textContent = "Checking...";
  try {
    const r = await fetch("api/status" + (force ? "?force=1" : ""));
    const j = await r.json();
    setStatus(j.state);
    $("meta").textContent = "Printer " + j.mac + " - channel " + j.channel + " - dither " + (j.dither ? "on" : "off");
  } catch (e) { setStatus("error"); }
}

$("file").addEventListener("change", (e) => {
  file = e.target.files[0] || null;
  $("fname").textContent = file ? file.name : "No file selected";
  $("print").disabled = !file;
  $("msg").className = "msg";
});

$("refresh").addEventListener("click", () => refresh(true));

$("print").addEventListener("click", async () => {
  if (!file) return;
  $("print").disabled = true; setStatus("printing");
  const m = $("msg"); m.className = "msg"; m.textContent = "";
  const fd = new FormData(); fd.append("pdf", file);
  try {
    const r = await fetch("api/print", { method: "POST", body: fd });
    const j = await r.json();
    if (j.ok) {
      m.className = "msg ok"; m.textContent = "Printed " + j.pages + " page" + (j.pages === 1 ? "" : "s") + ".";
    } else if (j.asleep) {
      m.className = "msg warn"; m.textContent = j.error;
    } else {
      m.className = "msg err"; m.textContent = j.error;
    }
  } catch (e) {
    m.className = "msg err"; m.textContent = "Request failed: " + e;
  } finally {
    $("print").disabled = !file;
    refresh(false);  // reflect the print's own result; don't reconnect immediately
  }
});

refresh(false);
</script>
</body>
</html>
"""


@app.get("/")
def index() -> Response:
    return Response(INDEX_HTML, mimetype="text/html")


@app.get("/api/status")
def api_status():
    force = request.args.get("force") in ("1", "true", "yes")
    return jsonify({
        "state": _status(force=force),
        "mac": MAC, "channel": CHANNEL, "dither": DITHER,
    })


@app.post("/api/print")
def api_print():
    global _printing
    f = request.files.get("pdf")
    if f is None or not f.filename:
        return jsonify({"ok": False, "error": "No PDF uploaded."}), 400

    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    f.save(path)
    try:
        with _bt_lock:
            _printing = True
            _status_cache.update(ts=time.time(), state="printing")
            try:
                n = ppa.print_pdf(path, MAC, dither=DITHER, channel=CHANNEL)
            finally:
                _printing = False
        _status_cache.update(ts=time.time(), state="online")
        return jsonify({"ok": True, "pages": n})
    except ppa.PrinterAsleep as e:
        _status_cache.update(ts=time.time(), state="asleep")
        return jsonify({"ok": False, "asleep": True, "error": str(e)})
    except ppa.TransportError as e:
        _status_cache.update(ts=time.time(), state="error")
        return jsonify({"ok": False, "error": str(e)})
    except Exception as e:
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"})
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


if __name__ == "__main__":
    from waitress import serve
    print(f"[peripage-a40] serving on :{PORT} (mac={MAC} ch={CHANNEL} dither={DITHER})", flush=True)
    serve(app, host="0.0.0.0", port=PORT)
