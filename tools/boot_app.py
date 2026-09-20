# Bypass the bootrom's BOOTSEL check: reboot directly to the application's
# reset vector. Flash stays in the bootrom's default XIP read mode (slower
# than boot2 would configure, but fully functional).
import glob, struct, time
from picoboot import Picoboot

pb = Picoboot()
pb.reset_interface()
pb.exit_xip()
pb.enter_cmd_xip()
sp, pc = struct.unpack("<II", pb.read(0x10000100, 8))
print("app entry: SP=0x%08x PC=0x%08x" % (sp, pc))

print("jumping directly to the application ...")
pb.reboot(pc, sp, 100)
pb.close()

for i in range(25):
    ports = glob.glob("/dev/cu.usbmodem*")
    if ports:
        print("SUCCESS - MicroPython is running at %s" % ports[0])
        raise SystemExit(0)
    time.sleep(1)
print("no serial port after 25s")
