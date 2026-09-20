import glob, time
from picoboot import Picoboot

pb = Picoboot()
pb.reset_interface()
print("connected, issuing plain reboot (no exclusive/eject) ...")
pb.reboot(0, 0, 100)
pb.close()

for i in range(25):
    ports = glob.glob("/dev/cu.usbmodem*")
    if ports:
        print("SUCCESS - MicroPython at %s" % ports[0])
        raise SystemExit(0)
    time.sleep(1)
print("still no serial port after 25s")
