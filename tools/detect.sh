#!/bin/bash
# Figure out what state the Pico is in.
echo "== USB serial ports =="
ls /dev/cu.usbmodem* 2>/dev/null || echo "(none)"
echo
echo "== BOOTSEL drive =="
ls -d /Volumes/RPI-RP2 2>/dev/null || echo "(not mounted)"
echo
echo "== USB device tree =="
system_profiler SPUSBDataType 2>/dev/null | grep -iA4 -e "pico" -e "rp2" -e "MicroPython" -e "Board in FS mode" || echo "(no RP2040/RP2350 device seen)"
