#!/usr/bin/with-contenv bashio

export PRINTER_MAC="$(bashio::config 'printer_mac')"
export RFCOMM_CHANNEL="$(bashio::config 'rfcomm_channel')"
export DITHER="$(bashio::config 'dither')"
export PORT=8099

bashio::log.info "PeriPage A40 print server starting"
bashio::log.info "Printer MAC: ${PRINTER_MAC}  channel: ${RFCOMM_CHANNEL}  dither: ${DITHER}"

exec python3 /app/server.py
