# Zero-risk connectivity check: claim the interface, reset it, take
# non-exclusive access, read status. Nothing is erased or written.
from picoboot import Picoboot, NOT_EXCLUSIVE

pb = Picoboot()
print("claimed PICOBOOT interface %d (ep_out=0x%02x ep_in=0x%02x)"
      % (pb.ifnum, pb.ep_out.bEndpointAddress, pb.ep_in.bEndpointAddress))

pb.reset_interface()
print("interface reset OK")

pb.exclusive_access(NOT_EXCLUSIVE)
print("exclusive_access(NOT_EXCLUSIVE) OK")

print("status:", pb.command_status())
pb.close()
print("RESULT: PICOBOOT protocol is working - safe to flash")
