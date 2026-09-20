# Step 2: drive the SSD1306 128x32 and show a visible self-test.
from machine import Pin, SoftI2C
from ssd1306 import SSD1306_I2C
import time

SDA, SCL, BUS = 0, 1, 0
W, H = 128, 32

i2c = SoftI2C(sda=Pin(SDA), scl=Pin(SCL), freq=400_000)
addrs = i2c.scan()
print("i2c devices:", [hex(a) for a in addrs])
if not addrs:
    raise SystemExit("No I2C device found - check wiring")

addr = 0x3C if 0x3C in addrs else addrs[0]
print("using address", hex(addr))
oled = SSD1306_I2C(W, H, i2c, addr=addr)

# 1. all pixels on - catches a dead/blank panel immediately
oled.fill(1)
oled.show()
print("test 1: full white")
time.sleep(1)

# 2. text
oled.fill(0)
oled.text("OLED OK", 0, 0)
oled.text("%dx%d @ %s" % (W, H, hex(addr)), 0, 10)
oled.text("SDA%d SCL%d" % (SDA, SCL), 0, 20)
oled.show()
print("test 2: text")
time.sleep(2)

# 3. border + diagonals - catches partial/shifted addressing
oled.fill(0)
oled.rect(0, 0, W, H, 1)
for x in range(0, W, 4):
    oled.pixel(x, int(x * (H - 1) / (W - 1)), 1)
    oled.pixel(x, H - 1 - int(x * (H - 1) / (W - 1)), 1)
oled.show()
print("test 3: border + X")
time.sleep(2)

# 4. invert flash
for _ in range(3):
    oled.invert(1); time.sleep(0.2)
    oled.invert(0); time.sleep(0.2)
print("test 4: invert flash")

# 5. animated counter - proves sustained I2C traffic
oled.fill(0)
for n in range(20):
    oled.fill_rect(0, 8, W, 16, 0)
    oled.text("count: %d" % n, 0, 12)
    oled.show()
    time.sleep(0.1)

oled.fill(0)
oled.text("ALL TESTS PASS", 0, 12)
oled.show()
print("RESULT: all display tests completed")
