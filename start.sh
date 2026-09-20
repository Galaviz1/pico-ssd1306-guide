#!/bin/bash
# Boot this Pico into MicroPython. Needed because its BOOTSEL button is stuck
# pressed, so the bootrom enters the bootloader at every reset.
cd "$(dirname "$0")/tools"
if ls /dev/cu.usbmodem* >/dev/null 2>&1; then
    echo "Already running MicroPython at $(ls /dev/cu.usbmodem* | head -1)"
    exit 0
fi
if ! system_profiler SPUSBDataType 2>/dev/null | grep -qi "RP2 Boot"; then
    echo "No Pico found. Plug it in and run this again."
    exit 1
fi
python3 boot2_jump.py "$@"
