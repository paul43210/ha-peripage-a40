"""PeriPage A40 HA add-on web server.

Printing runs as a background job so the HTTP request returns immediately and
never outlives Home Assistant's ingress proxy timeout. The page kicks off a
print, then polls /api/status until the job finishes.
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
STATUS_CACHE_TTL = 15.0

app = Flask(__name__)
_bt_lock = threading.Lock()      # serialize ALL dongle access (print + probe)
_job_lock = threading.Lock()
_job = {"state": "idle", "pages": 0, "message": "", "ts": 0.0}
_probe = {"ts": 0.0, "state": "unknown"}


def _set_job(**kw):
    with _job_lock:
        _job.update(ts=time.time(), **kw)


def _get_job():
    with _job_lock:
        return dict(_job)


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
    """online|asleep|error, retrying once on a transient error."""
    st = _probe_once()
    if st == "error":
        time.sleep(1.0)
        st = _probe_once()
    return st


def _connectivity(force: bool = False) -> str:
    now = time.time()
    if force or (now - _probe["ts"]) >= STATUS_CACHE_TTL:
        with _bt_lock:
            st = _probe_state()
        _probe.update(ts=time.time(), state=st)
    return _probe["state"]


def _worker(path: str):
    try:
        with _bt_lock:
            n = ppa.print_pdf(path, MAC, dither=DITHER, channel=CHANNEL)
        _set_job(state="done", pages=n,
                 message="Printed %d page%s." % (n, "" if n == 1 else "s"))
        _probe.update(ts=time.time(), state="online")
    except ppa.PrinterAsleep as e:
        _set_job(state="asleep", pages=0, message=str(e))
        _probe.update(ts=time.time(), state="asleep")
    except ppa.TransportError as e:
        _set_job(state="error", pages=0, message=str(e))
    except Exception as e:
        _set_job(state="error", pages=0, message="%s: %s" % (type(e).__name__, e))
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


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
let busy = false;

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

function showMsg(cls, text) {
  const m = $("msg");
  m.className = cls ? ("msg " + cls) : "msg";
  m.textContent = text || "";
}

async function getJSON(url, opts) {
  try {
    const r = await fetch(url, opts);
    const txt = await r.text();
    let data = null;
    try { data = JSON.parse(txt); } catch (e) { data = null; }
    return { ok: r.ok, status: r.status, data: data };
  } catch (e) {
    return { ok: false, status: 0, data: null };
  }
}

function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

async function refresh(force) {
  if (busy) return;
  setStatus("unknown"); $("statusText").textContent = "Checking...";
  const res = await getJSON("api/status" + (force ? "?force=1" : ""));
  if (res.data) {
    setStatus(res.data.state);
    $("meta").textContent = "Printer " + res.data.mac + " - channel " + res.data.channel +
      " - dither " + (res.data.dither ? "on" : "off");
  } else {
    setStatus("error");
  }
}

async function pollUntilDone() {
  const deadline = Date.now() + 120000;
  while (Date.now() < deadline) {
    await sleep(1500);
    const res = await getJSON("api/status");
    if (!res.data) continue;
    setStatus(res.data.state);
    const job = res.data.job || {};
    if (job.state && job.state !== "printing") {
      if (job.state === "done") showMsg("ok", job.message || "Done.");
      else if (job.state === "asleep") showMsg("warn", job.message || "Printer is asleep or off.");
      else showMsg("err", job.message || "Print failed.");
      return;
    }
  }
  showMsg("warn", "Still working - check the printer, then tap Refresh status.");
}

$("file").addEventListener("change", (e) => {
  file = e.target.files[0] || null;
  $("fname").textContent = file ? file.name : "No file selected";
  $("print").disabled = !file;
  showMsg("", "");
});

$("refresh").addEventListener("click", () => refresh(true));

$("print").addEventListener("click", async () => {
  if (!file || busy) return;
  busy = true;
  $("print").disabled = true;
  setStatus("printing");
  showMsg("", "");
  try {
    const fd = new FormData(); fd.append("pdf", file);
    const res = await getJSON("api/print", { method: "POST", body: fd });
    if (!res.data) {
      showMsg("err", "Could not start the print (server error " + res.status + ").");
    } else if (res.data.busy) {
      showMsg("warn", res.data.error || "A print is already in progress.");
    } else if (!res.data.ok) {
      showMsg("err", res.data.error || "Could not start the print.");
    } else {
      await pollUntilDone();
    }
  } finally {
    busy = false;
    $("print").disabled = !file;
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
    job = _get_job()
    if job["state"] == "printing":
        dot = "printing"
    else:
        force = request.args.get("force") in ("1", "true", "yes")
        dot = _connectivity(force=force)
    return jsonify({"state": dot, "job": job,
                    "mac": MAC, "channel": CHANNEL, "dither": DITHER})


@app.post("/api/print")
def api_print():
    if _get_job()["state"] == "printing":
        return jsonify({"ok": False, "busy": True,
                        "error": "A print is already in progress."}), 409
    f = request.files.get("pdf")
    if f is None or not f.filename:
        return jsonify({"ok": False, "error": "No PDF uploaded."}), 400
    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    f.save(path)
    _set_job(state="printing", pages=0, message="")
    threading.Thread(target=_worker, args=(path,), daemon=True).start()
    return jsonify({"ok": True, "started": True})


if __name__ == "__main__":
    from waitress import serve
    print("[peripage-a40] serving on :%d (mac=%s ch=%d dither=%s)"
          % (PORT, MAC, CHANNEL, DITHER), flush=True)
    serve(app, host="0.0.0.0", port=PORT)
