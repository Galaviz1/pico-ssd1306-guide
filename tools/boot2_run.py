# Replicate the bootrom's real boot path: copy the 256-byte boot2 stage into
# SRAM and execute it. boot2 configures the QSPI flash for XIP, sets VTOR,
# loads SP/PC from the app vector table and jumps - all self-contained.
import glob, struct, time
from firmware import find_uf2
from picoboot import Picoboot, EXCLUSIVE

BOOT2_RAM = 0x20041F00          # where the RP2040 bootrom stages boot2

raw = open(find_uf2(), "rb").read()
first = raw[0:512]
payload_size, = struct.unpack("<I", first[16:20])
target_addr,  = struct.unpack("<I", first[12:16])
boot2 = first[32:32 + payload_size]
print("boot2 from UF2: target=0x%08x size=%d" % (target_addr, len(boot2)))
assert target_addr == 0x10000000 and len(boot2) == 256

pb = Picoboot()
pb.reset_interface()
pb.exclusive_access(EXCLUSIVE)
pb.exit_xip()                   # leave flash in command mode, as boot2 expects
print("staged: exclusive access + exit_xip")

pb.write(BOOT2_RAM, boot2)
back = pb.read(BOOT2_RAM, 256)
print("boot2 copied to SRAM 0x%08x, readback %s"
      % (BOOT2_RAM, "matches" if back == boot2 else "MISMATCH"))
if back != boot2:
    raise SystemExit("SRAM copy failed")

print("executing boot2 ...")
pb.exec_ram(BOOT2_RAM | 1)      # thumb bit
pb.close()

for i in range(25):
    ports = glob.glob("/dev/cu.usbmodem*")
    if ports:
        print("SUCCESS - MicroPython is running at %s" % ports[0])
        raise SystemExit(0)
    time.sleep(1)
print("no serial port after 25s")
