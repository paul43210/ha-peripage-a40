# PeriPage A40 Print

Prints PDFs to a PeriPage A40 over Bluetooth Classic (RFCOMM/SPP) using the
printer's native page-mode protocol — no vendor app and no cloud.

## Configuration

| Option | Default | Notes |
|---|---|---|
| `printer_mac` | `04:7F:0E:B0:45:18` | Classic BT MAC of the A40 |
| `rfcomm_channel` | `1` | SPP channel |
| `dither` | `true` | Floyd–Steinberg dithering for grayscale |

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

## Using it

Open the **Web UI**, choose a PDF, press **Print**. The print runs as a
background job and the page reports the result when it finishes. The status
panel shows reachable / asleep / printing / last result, plus the **battery
percentage** when the printer is online.

## Waking the printer

The A40 drops its Bluetooth Classic radio when idle (its BLE beacon stays on, so
phones still "see" it). If status shows **Asleep / off** while the printer is
powered, press its power/feed button and tap **Refresh status**.

## Bluetooth requirements

Runs with `host_network: true` (required — `AF_BLUETOOTH` sockets only work in
the host network namespace), plus `host_dbus` and `NET_ADMIN`/`NET_RAW`. The
host needs a Bluetooth **Classic**-capable adapter in range of the printer.

## Print quality

Always prints at the printer's maximum density (concentration 2) and native
resolution; nothing higher to set. Paper-out is not detected (it is obvious from
the printer itself).
