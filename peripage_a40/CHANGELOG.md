# Changelog

## 0.1.5
- Show the printer **battery percentage** in the status panel (queried over
  Bluetooth in the same connection as the status check).

## 0.1.4
- Printing is now a background job: the Print button returns immediately and
  the page polls for the result, so a long print no longer hits the ingress
  proxy timeout (the cause of the "<html> ... is not valid JSON" error and
  the stuck "Printing..." status).
- The UI handles non-JSON / error responses gracefully.
- Core: Bluetooth send now has a timeout, so a stalled printer (out of paper
  or jammed) ends with a clear error instead of hanging.

## 0.1.3
- Fix: a successful print no longer flips the status to a false "Bluetooth
  error". The UI now reflects the print result instead of opening a fresh
  Bluetooth connection the instant the print connection closed.
- Status probe retries once on a transient error.

## 0.1.2
- Pin the core library to a commit so rebuilds actually reinstall it
  (a cached pip layer had kept the pre-fix core, so a sleeping printer
  still showed as a Bluetooth error). No functional change otherwise.

## 0.1.1
- Fix: enable `host_network` so the container can open Bluetooth (RFCOMM)
  sockets. Without the host network namespace the kernel refuses AF_BLUETOOTH
  with errno 97 (EAFNOSUPPORT).
- A sleeping/off printer now reports as "asleep" rather than a Bluetooth error
  (core library treats the connect timeout correctly).

## 0.1.0
- Initial add-on: web upload page (HA ingress) prints PDFs to the PeriPage A40
  via the native 1f page-mode protocol using the `peripage-a40` library.
- Coarse printer status: online / asleep-or-off / printing / last-job result.
- Known scope: battery %, paper-out and device error codes are not yet
  reverse-engineered (outbound print path only); planned for a later release.
