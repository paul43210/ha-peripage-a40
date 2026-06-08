# PeriPage A40 Print

Prints PDFs to a PeriPage A40 over Bluetooth Classic (RFCOMM/SPP) using the
printer's native page-mode protocol — no vendor app and no cloud.

## Configuration
| Option | Default | Notes |
|---|---|---|
| `printer_mac` | `04:7F:0E:B0:45:18` | Classic BT MAC of the A40 |
| `rfcomm_channel` | `1` | SPP channel |
| `dither` | `true` | Floyd–Steinberg dithering for grayscale |

## Using it
Open the add-on's **Web UI**, choose a PDF, press **Print**. The status panel
shows whether the printer is reachable.

If the printer is asleep or off the page reports it — press the printer's
power/feed button to wake it and try again.

## Bluetooth notes
The add-on talks to the host's Bluetooth adapter (the Sena UD100 dongle).
It runs with `host_network: true` (required -- AF_BLUETOOTH sockets can only be
created in the host network namespace), plus `host_dbus` and the
`NET_ADMIN`/`NET_RAW` capabilities.

## Status scope
v1 reports coarse status only (reachable / asleep / printing / last result).
Battery level and paper-out are not yet decoded and will arrive in a later
release.
