# Report what this RP2040 board actually is, measured rather than assumed.
# Runs on the Pico:  mpremote connect auto run board_info.py
import gc
import machine
import os
import sys
import ubinascii

FLASH_TOTAL = 2 * 1024 * 1024        # Pico carries 2 MB of QSPI flash


def kb(n):
    return "%.1f KB" % (n / 1024.0)


print("=" * 46)
print(" RP2040 board report")
print("=" * 46)

print("\n[identity]")
print("  board       :", sys.implementation._machine)
print("  unique id   :", ubinascii.hexlify(machine.unique_id()).decode().upper())
print("  build       :", sys.implementation._build)
print("  micropython : %d.%d.%d" % sys.implementation.version[:3])
print("  platform    :", sys.platform)

print("\n[clock]")
freq = machine.freq()
print("  system      : %d Hz (%.0f MHz)" % (freq, freq / 1e6))

print("\n[ram]")
gc.collect()
free, used = gc.mem_free(), gc.mem_alloc()
print("  heap free   :", kb(free))
print("  heap used   :", kb(used))
print("  heap total  :", kb(free + used))
print("  (RP2040 has 264 KB SRAM; the rest is static allocations and stack)")

print("\n[flash]")
st = os.statvfs("/")
bsize, total, bfree = st[0], st[2], st[3]
fs_total, fs_free = total * bsize, bfree * bsize
fw_region = FLASH_TOTAL - fs_total
print("  total       :", kb(FLASH_TOTAL))
print("  firmware    : %s region" % kb(fw_region))
print("  filesystem  : %s total, %s free, %s used"
      % (kb(fs_total), kb(fs_free), kb(fs_total - fs_free)))
print("  block size  :", bsize)

print("\n[temperature]")
try:
    volts = machine.ADC(4).read_u16() * 3.3 / 65535
    print("  on-die      : %.1f C" % (27 - (volts - 0.706) / 0.001721))
except Exception as exc:
    print("  unavailable :", exc)

print("\n[bootsel]")
try:
    import rp2
    pressed = rp2.bootsel_button()
    print("  button      :", "PRESSED" if pressed else "not pressed")
    if pressed:
        print("  WARNING: reads pressed with nobody touching it.")
        print("  A stuck BOOTSEL makes the bootrom enter the bootloader at")
        print("  every reset, so the board never runs your code - while flash")
        print("  reads and writes still work perfectly. See the README.")
except (ImportError, AttributeError):
    print("  unavailable : needs MicroPython 1.20+ on rp2")

print("\n" + "=" * 46)
