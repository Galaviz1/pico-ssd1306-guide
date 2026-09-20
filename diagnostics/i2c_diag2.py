from machine import Pin, I2C, SoftI2C
import time

def try_op(label, fn):
    try:
        r = fn()
        print("  %-34s OK%s" % (label, "" if r is None else " -> %s" % r))
        return True
    except OSError as e:
        print("  %-34s FAIL (%s)" % (label, e))
        return False

for name, mk in (("hardware I2C0 @100k", lambda: I2C(0, sda=Pin(0), scl=Pin(1), freq=100_000)),
                 ("SoftI2C (bit-banged) @100k", lambda: SoftI2C(sda=Pin(0), scl=Pin(1), freq=100_000))):
    print("\n=== %s ===" % name)
    i2c = mk()
    print("  scan -> %s" % [hex(a) for a in i2c.scan()])
    for addr in (0x3C, 0x3D):
        print("  -- address 0x%02x --" % addr)
        try_op("writeto 0 bytes (addr only)", lambda: i2c.writeto(addr, b""))
        try_op("writeto 1 byte  b'\\x00'",     lambda: i2c.writeto(addr, b"\x00"))
        try_op("writeto 2 bytes b'\\x80\\xAE'", lambda: i2c.writeto(addr, b"\x80\xAE"))
        try_op("writeto 2 bytes b'\\x00\\xAE'", lambda: i2c.writeto(addr, b"\x00\xAE"))
        try_op("readfrom 1 byte",              lambda: i2c.readfrom(addr, 1))
