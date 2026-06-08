# Changelog

## 0.1.0
- Initial add-on: web upload page (HA ingress) prints PDFs to the PeriPage A40
  via the native 1f page-mode protocol using the `peripage-a40` library.
- Coarse printer status: online / asleep-or-off / printing / last-job result.
- Known scope: battery %, paper-out and device error codes are not yet
  reverse-engineered (outbound print path only); planned for a later release.
