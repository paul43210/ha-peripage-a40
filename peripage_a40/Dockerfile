# Supervisor >= 2026.04.0 no longer injects BUILD_FROM; use an explicit, pinned FROM.
FROM ghcr.io/home-assistant/amd64-base-python:3.13-alpine3.23

# Core lib pinned to a commit SHA: changing it both updates the core AND
# busts Docker's layer cache so the new code is actually reinstalled.
# git is needed only to pip-install the core library from GitHub, then removed.
# pillow + pypdfium2 install from musllinux wheels (no compiler needed). If a
# future version lacks a musl wheel, add: build-base jpeg-dev zlib-dev.
RUN apk add --no-cache git \
 && pip install --no-cache-dir \
      flask waitress \
      "git+https://github.com/paul43210/peripage-a40@04dc4f1" \
 && apk del git

COPY app /app
COPY run.sh /
RUN chmod a+x /run.sh

LABEL \
  io.hass.name="PeriPage A40 Print" \
  io.hass.version="0.1.4" \
  io.hass.type="addon" \
  io.hass.arch="amd64"

CMD [ "/run.sh" ]
