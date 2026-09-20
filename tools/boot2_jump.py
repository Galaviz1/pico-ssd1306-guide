# boot2's exit routine: "if LR == 0, vector into flash, else return to caller".
# PC_EXEC calls with a real LR, so boot2 returns instead of booting. This stub
# zeroes LR and tail-calls boot2, reproducing how the bootrom enters it.
#
#   2000        movs r0, #0
#   4686        mov  lr, r0
#   4900        ldr  r1, [pc, #0]     -> literal at stub+8
#   4708        bx   r1
#   .word boot2_entry | 1
import glob, struct, time
from firmware import find_uf2
from picoboot import Picoboot, EXCLUSIVE

BOOT2_RAM = 0x20041F00
STUB_RAM  = 0x20041E00

stub = struct.pack("<HHHHI", 0x2000, 0x4686, 0x4900, 0x4708, BOOT2_RAM | 1)
assert len(stub) == 12

raw = open(find_uf2(), "rb").read()
boot2 = raw[32:32 + 256]

pb = Picoboot()
pb.reset_interface()
pb.exclusive_access(EXCLUSIVE)
pb.exit_xip()                       # boot2 expects flash in command mode
print("exclusive access + exit_xip")

pb.write(BOOT2_RAM, boot2)
pb.write(STUB_RAM, stub)
ok_b = pb.read(BOOT2_RAM, 256) == boot2
ok_s = pb.read(STUB_RAM, 12) == stub
print("boot2 in SRAM: %s   stub in SRAM: %s" % (ok_b, ok_s))
print("stub bytes: %s" % stub.hex())
if not (ok_b and ok_s):
    raise SystemExit("SRAM staging failed")

print("executing stub (LR=0 -> boot2 -> flash) ...")
pb.exec_ram(STUB_RAM | 1)
pb.close()

for i in range(25):
    ports = glob.glob("/dev/cu.usbmodem*")
    if ports:
        print("SUCCESS - MicroPython is running at %s" % ports[0])
        raise SystemExit(0)
    time.sleep(1)
print("no serial port after 25s")
