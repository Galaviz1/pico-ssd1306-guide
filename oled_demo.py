# Blinking text on the SSD1306 128x32.
# SoftI2C on GP0/GP1 - the RP2040 hardware I2C block misbehaves on this board.
#
# THIS FILE RUNS ON THE PICO, NOT ON YOUR MAC.
import sys

if sys.implementation.name != "micropython":
    print("\n" + "=" * 62)
    print("  This script runs ON THE PICO, not on your Mac.")
    print("=" * 62)
    print("""
'machine' is part of MicroPython, built into the Pico's firmware.
It is not a package and cannot be pip-installed.

You pressed VS Code's Play button, which uses your Mac's Python.
Instead, run it on the board:

  In VS Code:  press  Shift + Cmd + B
  In Terminal: python3 -m mpremote connect auto run oled_demo.py

To stop it once running: Ctrl-C in that terminal panel.
""")
    raise SystemExit(1)

from machine import Pin, SoftI2C
from ssd1306 import SSD1306_I2C
import time

ON_MS = 1000          # text visible
OFF_MS = 1000         # text hidden

i2c = SoftI2C(sda=Pin(0), scl=Pin(1), freq=400_000)
oled = SSD1306_I2C(128, 32, i2c, addr=0x3C)


def draw(visible):
    oled.fill(0)
    if visible:
        oled.text("Hello, Pi Pico!", 0, 4)
        oled.text("SSD1306 128x32", 0, 18)
    oled.show()


try:
    while True:
        draw(True)
        time.sleep_ms(ON_MS)
        draw(False)
        time.sleep_ms(OFF_MS)
except KeyboardInterrupt:
    oled.fill(0)          # leave the panel blank on Ctrl-C
    oled.show()
