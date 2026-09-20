import usb.core, usb.util, usb.backend.libusb1

be = usb.backend.libusb1.get_backend(find_library=lambda x: "/usr/local/opt/libusb/lib/libusb-1.0.dylib")
dev = usb.core.find(idVendor=0x2E8A, backend=be)
if dev is None:
    raise SystemExit("No 2e8a device found")

print("device: %04x:%04x  bus=%s addr=%s" % (dev.idVendor, dev.idProduct, dev.bus, dev.address))
try:
    print("manufacturer:", usb.util.get_string(dev, dev.iManufacturer))
    print("product:     ", usb.util.get_string(dev, dev.iProduct))
    print("serial:      ", usb.util.get_string(dev, dev.iSerialNumber))
except Exception as e:
    print("(string descriptors unreadable: %s)" % e)

for cfg in dev:
    print("\nconfiguration", cfg.bConfigurationValue)
    for intf in cfg:
        print("  interface %d alt %d  class=0x%02x subclass=0x%02x proto=0x%02x"
              % (intf.bInterfaceNumber, intf.bAlternateSetting,
                 intf.bInterfaceClass, intf.bInterfaceSubClass, intf.bInterfaceProtocol))
        if intf.bInterfaceClass == 0xFF:
            print("    ^^ VENDOR-SPECIFIC = PICOBOOT")
        for ep in intf:
            d = "IN" if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN else "OUT"
            print("    endpoint 0x%02x %-3s maxpacket=%d" % (ep.bEndpointAddress, d, ep.wMaxPacketSize))
