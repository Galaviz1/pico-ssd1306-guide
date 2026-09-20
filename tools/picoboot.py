"""Minimal PICOBOOT driver for the RP2040 bootrom (USB 2e8a:0003).

Protocol per RP2040 datasheet 2.8.5. Commands are 32-byte packets on the
vendor interface's bulk OUT endpoint, followed by an optional data phase and
a zero-length ack in the opposite direction.
"""
import struct
import usb.core
import usb.util
import usb.backend.libusb1

def _find_libusb():
    """pyusb cannot always locate libusb on macOS; check the usual places."""
    import ctypes.util
    import os
    for p in ("/opt/homebrew/lib/libusb-1.0.dylib",          # Apple Silicon brew
              "/usr/local/opt/libusb/lib/libusb-1.0.dylib",  # Intel brew
              "/usr/local/lib/libusb-1.0.dylib",
              "/usr/lib/x86_64-linux-gnu/libusb-1.0.so.0"):  # Debian/Ubuntu
        if os.path.exists(p):
            return p
    return ctypes.util.find_library("usb-1.0")


LIBUSB = _find_libusb()

VID = 0x2E8A
PID_RP2040 = 0x0003

CMD_MAGIC = 0x431FD10B

PC_EXCLUSIVE_ACCESS = 0x01
PC_REBOOT           = 0x02
PC_FLASH_ERASE      = 0x03
PC_READ             = 0x84   # top bit = device-to-host
PC_WRITE            = 0x05
PC_EXIT_XIP         = 0x06
PC_EXEC             = 0x08
PC_ENTER_CMD_XIP    = 0x07

NOT_EXCLUSIVE        = 0
EXCLUSIVE            = 1
EXCLUSIVE_AND_EJECT  = 2

IF_RESET           = 0x41
GET_COMMAND_STATUS = 0x42

FLASH_BASE   = 0x10000000
SECTOR_SIZE  = 4096
PAGE_SIZE    = 256


class PicobootError(Exception):
    pass


class Picoboot:
    def __init__(self):
        be = usb.backend.libusb1.get_backend(find_library=lambda x: LIBUSB)
        if be is None:
            raise PicobootError(
                "libusb not found. Install it:  brew install libusb  (macOS)\n"
                "                                apt install libusb-1.0-0  (Debian/Ubuntu)")
        self.dev = usb.core.find(idVendor=VID, idProduct=PID_RP2040, backend=be)
        if self.dev is None:
            raise PicobootError("No RP2040 in BOOTSEL mode (2e8a:0003) found")

        cfg = self.dev.get_active_configuration()
        self.intf = None
        for i in cfg:
            if i.bInterfaceClass == 0xFF:
                self.intf = i
                break
        if self.intf is None:
            raise PicobootError("No vendor-specific (PICOBOOT) interface on device")

        self.ifnum = self.intf.bInterfaceNumber
        self.ep_out = self.ep_in = None
        for ep in self.intf:
            if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_OUT:
                self.ep_out = ep
            else:
                self.ep_in = ep
        if self.ep_out is None or self.ep_in is None:
            raise PicobootError("PICOBOOT interface missing bulk endpoints")

        try:
            if self.dev.is_kernel_driver_active(self.ifnum):
                self.dev.detach_kernel_driver(self.ifnum)
        except (NotImplementedError, usb.core.USBError):
            pass  # macOS: vendor interface has no kernel driver to detach

        usb.util.claim_interface(self.dev, self.ifnum)
        self.token = 0

    # --- control transfers -------------------------------------------------
    def reset_interface(self):
        self.dev.ctrl_transfer(0x41, IF_RESET, 0, self.ifnum, None, 3000)

    def command_status(self):
        raw = self.dev.ctrl_transfer(0xC1, GET_COMMAND_STATUS, 0, self.ifnum, 16, 3000)
        token, status, cmd_id, in_progress = struct.unpack("<IIBB", bytes(raw)[:10])
        return {"token": token, "status": status, "cmd_id": cmd_id,
                "in_progress": bool(in_progress)}

    # --- command plumbing --------------------------------------------------
    def _packet(self, cmd_id, args, transfer_len):
        if len(args) > 16:
            raise PicobootError("args too long")
        self.token += 1
        hdr = struct.pack("<IIBBHI", CMD_MAGIC, self.token, cmd_id,
                          len(args), 0, transfer_len)
        return hdr + args + b"\x00" * (16 - len(args))

    def _cmd(self, cmd_id, args=b"", data=None, read_len=0, timeout=10000):
        transfer_len = read_len if read_len else (len(data) if data else 0)
        self.ep_out.write(self._packet(cmd_id, args, transfer_len), timeout)

        if read_len:
            buf = self.ep_in.read(read_len, timeout)
            self.ep_out.write(b"", timeout)          # zero-length ack
            return bytes(buf)
        if data:
            self.ep_out.write(data, timeout)
            self.ep_in.read(0, timeout)              # zero-length ack
            return None
        self.ep_in.read(0, timeout)
        return None

    # --- commands ----------------------------------------------------------
    def exclusive_access(self, mode):
        self._cmd(PC_EXCLUSIVE_ACCESS, struct.pack("<B", mode))

    def exit_xip(self):
        self._cmd(PC_EXIT_XIP)

    def enter_cmd_xip(self):
        self._cmd(PC_ENTER_CMD_XIP)

    def flash_erase(self, addr, size):
        if addr % SECTOR_SIZE or size % SECTOR_SIZE:
            raise PicobootError("erase must be 4096-byte aligned")
        self._cmd(PC_FLASH_ERASE, struct.pack("<II", addr, size), timeout=60000)

    def write(self, addr, data):
        self._cmd(PC_WRITE, struct.pack("<II", addr, len(data)), data=data)

    def read(self, addr, size):
        return self._cmd(PC_READ, struct.pack("<II", addr, size), read_len=size)

    def exec_ram(self, addr):
        """Execute code at addr. Never returns if the code takes over."""
        try:
            self._cmd(PC_EXEC, struct.pack("<I", addr), timeout=2000)
        except usb.core.USBError:
            pass  # expected: the bootrom's USB stack dies when control is handed off

    def reboot(self, pc=0, sp=0, delay_ms=500):
        try:
            self._cmd(PC_REBOOT, struct.pack("<III", pc, sp, delay_ms), timeout=1000)
        except usb.core.USBError:
            pass  # device drops off the bus as it reboots

    def close(self):
        try:
            usb.util.release_interface(self.dev, self.ifnum)
            usb.util.dispose_resources(self.dev)
        except usb.core.USBError:
            pass
