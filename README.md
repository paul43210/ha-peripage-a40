# PeriPage A40 — Home Assistant Add-on

Print PDFs to a **PeriPage A40** thermal printer straight from Home Assistant —
**no vendor app, no cloud, no account.** A small web page (served through HA
ingress) lets you upload a PDF and prints it over Bluetooth using the printer's
native page-mode protocol, so pages seek to top-of-form and line up with the
perforation exactly like the official app.

The Bluetooth/print engine is the companion library
[`paul43210/peripage-a40`](https://github.com/paul43210/peripage-a40); this repo
packages it as an installable Home Assistant add-on.

## Features

- Upload a PDF from any device on your network and print it — multi-page works,
  cuts line up with the perforation.
- Live status panel: online / asleep-or-off / printing / last result, **plus the
  printer's battery percentage**.
- Prints at the printer's **maximum** density/resolution.
- Fully local: talks directly to the printer's Bluetooth; nothing leaves your LAN.

## Install

1. Settings → Add-ons → Add-on Store → ⋮ (top-right) → **Repositories**.
2. Add `https://github.com/paul43210/ha-peripage-a40` and close.
3. Install **PeriPage A40 Print**.
4. In *Configuration*, set `printer_mac` to your printer's Bluetooth MAC if it
   differs from the default, then **Start** and open the **Web UI**.

> This add-on is `amd64`-only (built for an Intel/AMD HA host such as a Beelink
> mini PC) and requires a Bluetooth **Classic** adapter on the host.

## Configuration

| Option | Default | Notes |
|---|---|---|
| `printer_mac` | `04:7F:0E:B0:45:18` | The A40's Bluetooth Classic MAC |
| `rfcomm_channel` | `1` | RFCOMM/SPP channel |
| `dither` | `true` | Floyd–Steinberg dithering for grayscale/photos |

## Using it

Open the **Web UI**, choose a PDF, press **Print**. The job runs in the
background and the page shows the result ("Printed N pages") when it finishes.

The A40 keeps its Bluetooth Classic radio awake only for a while after it is
powered on or used. If it has been idle, the status reads **Asleep / off** even
though the green light is on — just tap the printer's power/feed button to wake
it and hit **Refresh status**.

## How it works

```
Browser (HA ingress)  ──>  add-on web server (Flask/waitress, :8099)
                              ├─ render PDF  (pypdfium2 → 1-bit raster)
                              ├─ encode      (native 1f page-mode blocks)
                              └─ send        (RFCOMM via host BlueZ / USB dongle)
```

Bluetooth Classic (`AF_BLUETOOTH`) sockets can only be created in the **host
network namespace**, so the add-on runs with `host_network: true` plus
`host_dbus` and the `NET_ADMIN`/`NET_RAW` capabilities. Printing is a background
job, so a long print never blocks or times out the request.

## Security notes

- Because Bluetooth requires `host_network`, the web server's port (`8099`) is
  reachable on your **LAN**, not only through Home Assistant's authenticated
  ingress. On a trusted home network this is low-risk (someone would only be
  able to print a page or read the battery level), but be aware of it. It can be
  locked down with a source-restriction in front of the add-on if desired.
- Uploads are capped at 25 MB and only one print runs at a time.
- No credentials or secrets are stored in this repo; the printer MAC is the only
  identifier and lives in the add-on options.

## Finding your printer's MAC

The add-on needs your printer's Bluetooth **Classic** MAC address (format
`AA:BB:CC:DD:EE:FF`). It does **not** scan automatically, so find it once and
paste it into the add-on's *Configuration* tab:

- **Official PeriPage app** — pair the printer, then look at its device/about
  screen.
- **Your phone's Bluetooth screen** — power the printer on and look for a
  `PeriPage_A40` device; most Android phones show the address in the device
  details (iOS hides it).
- **A Linux box with Bluetooth** — run `bluetoothctl`, then `scan on`, and watch
  for a line naming `PeriPage_A40`. Power-cycle the printer right before
  scanning — it only advertises for a short window after power-on.

Until a valid MAC is set, the add-on's status panel shows **Not configured**.

## Add-ons in this repository

- **peripage_a40** — *PeriPage A40 Print* (web upload + status panel).

## License

MIT — see [LICENSE](LICENSE).
