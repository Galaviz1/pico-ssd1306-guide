#!/bin/bash
# Flash MicroPython to a Pico in BOOTSEL mode by writing the UF2 to the raw
# block device. The RP2 bootloader scans incoming USB-MSC sectors for the UF2
# magic, so this works even when the FAT write path does not.
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
UF2="${1:-$(ls "$REPO"/RPI_PICO-*.uf2 2>/dev/null | tail -1)}"

[ -n "$UF2" ] && [ -f "$UF2" ] || { echo "ABORT: no RPI_PICO-*.uf2 in $REPO - download from https://micropython.org/download/RPI_PICO/"; exit 1; }

SZ=$(stat -f%z "$UF2")
[ $((SZ % 512)) -eq 0 ] || { echo "ABORT: $UF2 is not a whole number of 512B sectors"; exit 1; }
head -c 4 "$UF2" | grep -q 'UF2' || { echo "ABORT: $UF2 does not start with the UF2 magic"; exit 1; }

# --- positively identify the target, never hardcode a disk number ---
PART=$(diskutil list | awk '/RPI-RP2/ {print $NF}')
[ -n "$PART" ] || { echo "ABORT: no RPI-RP2 volume found. Is the Pico plugged in and in BOOTSEL?"; exit 1; }
[ "$(echo "$PART" | wc -l | tr -d ' ')" = "1" ] || { echo "ABORT: multiple RPI-RP2 volumes found, refusing to guess"; exit 1; }
DISK=$(echo "$PART" | sed 's/s[0-9]*$//')

# cross-check: must be the RP2 bootloader's own 134MB virtual disk
INFO=$(diskutil info "$DISK")
echo "$INFO" | grep -q "Device / Media Name: *RP2" || {
    echo "ABORT: $DISK does not report itself as RP2 media. Refusing to write."
    echo "$INFO" | grep -i -e "Media Name" -e "Disk Size" -e "Protocol"
    exit 1
}
SIZE_BYTES=$(echo "$INFO" | awk -F'[()]' '/Disk Size/ {print $2}' | awk '{print $1}')
[ "$SIZE_BYTES" = "134217728" ] || { echo "ABORT: $DISK is $SIZE_BYTES bytes, expected 134217728 (RP2 bootloader)"; exit 1; }

echo "Target confirmed: /dev/$DISK (RP2 bootloader, 134.2 MB)"
echo "Writing $SZ bytes ($((SZ/512)) sectors) of MicroPython v1.29.0 ..."

diskutil unmountDisk "/dev/$DISK" >/dev/null 2>&1
dd if="$UF2" of="/dev/r$DISK" bs=512 2>&1 | tail -3

echo "Write issued. Waiting for the board to reboot into MicroPython ..."
for i in $(seq 1 30); do
  if ls /dev/cu.usbmodem* >/dev/null 2>&1; then
    echo "SUCCESS - MicroPython is running at $(ls /dev/cu.usbmodem* | head -1)"
    exit 0
  fi
  sleep 1
done
echo "No serial port after 30s."
ls -d /Volumes/RPI-RP2 >/dev/null 2>&1 && echo "Still in BOOTSEL - the write did not take."
exit 1
