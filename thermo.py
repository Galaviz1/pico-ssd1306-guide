# Live temperature sparkline on a 128x32 SSD1306.
#
# Reads the RP2040's on-die temperature sensor (ADC channel 4) and scrolls a
# filled area chart. Pinch the chip and the trace climbs within a second or two,
# which is the whole point: cause and effect you can see.
#
# SoftI2C on GP0/GP1 - the RP2040 hardware I2C block does not work with this
# display. See the README.
from machine import Pin, SoftI2C, ADC
from ssd1306 import SSD1306_I2C
import time

W, H = 128, 32
HEADER_H = 9                 # text row plus the rule under it
GRAPH_TOP = HEADER_H
GRAPH_H = H - GRAPH_TOP      # 23 px of chart

SAMPLE_MS = 150              # ~6.7 samples/sec -> 128 px is ~19 s of history
OVERSAMPLE = 32              # the sensor is noisy; average it down
MIN_SPAN_C = 2.0             # never zoom in tighter than this, or noise fills the screen

CONV = 3.3 / 65535           # 16-bit ADC reading -> volts

i2c = SoftI2C(sda=Pin(0), scl=Pin(1), freq=400_000)
oled = SSD1306_I2C(W, H, i2c, addr=0x3C)
sensor = ADC(4)


def read_temp():
    """Datasheet transfer function, oversampled to calm the noise."""
    total = 0
    for _ in range(OVERSAMPLE):
        total += sensor.read_u16()
    volts = (total / OVERSAMPLE) * CONV
    return 27 - (volts - 0.706) / 0.001721


def draw(history, now, peak):
    lo, hi = min(history), max(history)
    span = hi - lo
    if span < MIN_SPAN_C:                    # keep a stable window when it's flat
        mid = (lo + hi) / 2
        lo, hi = mid - MIN_SPAN_C / 2, mid + MIN_SPAN_C / 2
        span = MIN_SPAN_C

    oled.fill(0)
    oled.text("%.1fC  MAX %.1f" % (now, peak), 0, 0)
    oled.hline(0, HEADER_H - 1, W, 1)

    # newest sample enters from the right
    x0 = W - len(history)
    for i, value in enumerate(history):
        scaled = int((value - lo) / span * (GRAPH_H - 1))
        y = GRAPH_TOP + GRAPH_H - 1 - scaled
        oled.vline(x0 + i, y, H - y, 1)      # fill to the bottom edge

    oled.show()


def main():
    first = read_temp()
    history = [first] * W                    # start full and flat, so the rise reads clearly
    peak = first

    while True:
        now = read_temp()
        history.append(now)
        del history[0]
        if now > peak:
            peak = now
        draw(history, now, peak)
        time.sleep_ms(SAMPLE_MS)


try:
    main()
except KeyboardInterrupt:
    oled.fill(0)
    oled.show()
