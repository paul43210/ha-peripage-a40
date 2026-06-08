# PeriPage A40 — Home Assistant Add-on Repository

A Home Assistant add-on that prints PDFs to a **PeriPage A40** thermal printer
over Bluetooth — **no vendor app, no cloud**. It uses the printer's native
page-mode (`1f`) protocol, so pages seek to top-of-form and cut at the
perforation just like the official app.

The Bluetooth/print engine lives in the companion library
[`paul43210/peripage-a40`](https://github.com/paul43210/peripage-a40); this
repo wraps it as an installable HA add-on with a web upload page.

## Install
1. Settings → Add-ons → Add-on Store → ⋮ → **Repositories**.
2. Add `https://github.com/paul43210/ha-peripage-a40`.
3. Install **PeriPage A40 Print**, set the printer MAC in *Configuration*, start it,
   and open the **Web UI** (ingress).

## Add-ons
- **peripage_a40** — PeriPage A40 Print (web upload + status panel).
