import struct
from picoboot import Picoboot

def crc32_mpeg2(data):
    """poly 0x04C11DB7, init 0xFFFFFFFF, no reflection, no final xor."""
    crc = 0xFFFFFFFF
    for b in data:
        crc ^= b << 24
        for _ in range(8):
            crc = ((crc << 1) ^ 0x04C11DB7) & 0xFFFFFFFF if crc & 0x80000000 \
                  else (crc << 1) & 0xFFFFFFFF
    return crc

pb = Picoboot()
pb.reset_interface()
pb.exit_xip()
pb.enter_cmd_xip()
boot2 = pb.read(0x10000000, 256)
vect  = pb.read(0x10000100, 8)
pb.close()

stored, = struct.unpack("<I", boot2[252:256])
calc = crc32_mpeg2(boot2[:252])
print("boot2 first 16 bytes: %s" % boot2[:16].hex())
print("stored checksum:  0x%08x" % stored)
print("computed (MPEG2): 0x%08x" % calc)
print("boot2 VALID -> bootrom will run this image" if stored == calc
      else "boot2 checksum MISMATCH -> bootrom would refuse to boot")

sp, pc = struct.unpack("<II", vect)
print("\napp vector table @0x10000100:  initial SP=0x%08x  reset PC=0x%08x" % (sp, pc))
ok_sp = 0x20000000 <= sp <= 0x20042000
ok_pc = 0x10000000 <= pc <= 0x10200000
print("SP in SRAM: %s   PC in flash: %s" % (ok_sp, ok_pc))
print("blank (0xFFFFFFFF)? %s" % (sp == 0xFFFFFFFF or pc == 0xFFFFFFFF))
