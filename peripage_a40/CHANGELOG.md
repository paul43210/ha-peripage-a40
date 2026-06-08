# Changelog

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
