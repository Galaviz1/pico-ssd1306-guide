# The address probe passes but command writes NAK. Walk the bus speed down and
# test a real multi-byte transfer at each step.
from machine import Pin, I2C
import time

ADDR = 0x3C
for freq in (400_000, 200_000, 100_000, 50_000, 20_000):
    try:
        i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=freq)
        found = i2c.scan()
        if ADDR not in found:
            print("%6d Hz: scan -> %s (0x3c absent)" % (freq, [hex(a) for a in found]))
            continue
        # display off - a single 2-byte command write
        i2c.writeto(ADDR, bytes([0x80, 0xAE]))
        # a longer burst, like init_display does
        for _ in range(10):
            i2c.writeto(ADDR, bytes([0x80, 0xA4]))
        # a data-sized write, like show() does
        i2c.writeto(ADDR, b"\x40" + bytes(128))
        print("%6d Hz: scan OK, cmd OK, burst OK, data OK  <-- WORKS" % freq)
    except OSError as e:
        print("%6d Hz: %s" % (freq, e))
    time.sleep(0.1)

print()
print("--- pull-up check: read idle line levels with internal pulls off ---")
sda = Pin(0, Pin.IN)
scl = Pin(1, Pin.IN)
time.sleep(0.05)
print("SDA idle =", sda.value(), " SCL idle =", scl.value())
print("(both should read 1 - if 0, that line is shorted low or unpowered)")
