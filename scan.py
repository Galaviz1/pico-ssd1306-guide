# Step 1: prove the Pico can see the OLED on the I2C bus.
from machine import Pin, I2C
import sys

CANDIDATES = [
    ("I2C0", 0, 0, 1),   # SDA=GP0, SCL=GP1
    ("I2C0", 0, 4, 5),
    ("I2C1", 1, 2, 3),
    ("I2C1", 1, 6, 7),
    ("I2C1", 1, 26, 27),
]

print("MicroPython:", sys.version)
print("scanning I2C buses...")
found = False
for name, bus, sda, scl in CANDIDATES:
    try:
        i2c = I2C(bus, sda=Pin(sda), scl=Pin(scl), freq=400_000)
        devices = i2c.scan()
    except Exception as e:
        print("  %s SDA=GP%-2d SCL=GP%-2d -> error: %s" % (name, sda, scl, e))
        continue
    if devices:
        found = True
        print("  %s SDA=GP%-2d SCL=GP%-2d -> FOUND %s"
              % (name, sda, scl, [hex(d) for d in devices]))
    else:
        print("  %s SDA=GP%-2d SCL=GP%-2d -> nothing" % (name, sda, scl))

print("RESULT:", "device(s) found" if found else "no I2C devices - check wiring")
