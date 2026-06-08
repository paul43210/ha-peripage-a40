# Supervisor >= 2026.04.0 no longer injects BUILD_FROM; use an explicit, pinned FROM.
FROM ghcr.io/home-assistant/amd64-base-python:3.13-alpine3.23

# git is needed only to pip-install the core library from GitHub, then removed.
# pillow + pypdfium2 install from musllinux wheels (no compiler needed). If a
# future version lacks a musl wheel, add: build-base jpeg-dev zlib-dev.
RUN apk add --no-cache git \
 && pip install --no-cache-dir \
      flask waitress \
      "git+https://github.com/paul43210/peripage-a40@main" \
 && apk del git

COPY app /app
COPY run.sh /
RUN chmod a+x /run.sh

LABEL \
  io.hass.name="PeriPage A40 Print" \
  io.hass.version="0.1.0" \
  io.hass.type="addon" \
  io.hass.arch="amd64"

CMD [ "/run.sh" ]
