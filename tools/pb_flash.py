"""Flash a UF2 to an RP2040 over PICOBOOT. No root required."""
import struct
import sys
import time

from picoboot import (Picoboot, EXCLUSIVE_AND_EJECT, FLASH_BASE,
                      SECTOR_SIZE, PAGE_SIZE)

UF2_MAGIC_START0 = 0x0A324655
UF2_MAGIC_START1 = 0x9E5D5157
UF2_MAGIC_END    = 0x0AB16F30
RP2040_FAMILY    = 0xE48BFF56
FLAG_FAMILY_ID   = 0x00002000
FLAG_NOT_MAIN    = 0x00000001


def parse_uf2(path):
    """Return (base_addr, image_bytes). Rejects anything non-contiguous."""
    with open(path, "rb") as f:
        raw = f.read()
    if len(raw) % 512:
        raise SystemExit("UF2 length %d is not a multiple of 512" % len(raw))

    chunks = {}
    total = len(raw) // 512
    for i in range(total):
        b = raw[i * 512:(i + 1) * 512]
        m0, m1, flags, addr, size, blkno, numblk, famid = struct.unpack("<8I", b[:32])
        mend, = struct.unpack("<I", b[508:512])
        if m0 != UF2_MAGIC_START0 or m1 != UF2_MAGIC_START1 or mend != UF2_MAGIC_END:
            raise SystemExit("block %d: bad UF2 magic" % i)
        if flags & FLAG_NOT_MAIN:
            continue
        if (flags & FLAG_FAMILY_ID) and famid != RP2040_FAMILY:
            raise SystemExit("block %d: family 0x%08x is not RP2040 (0x%08x)"
                             % (i, famid, RP2040_FAMILY))
        if size > 476:
            raise SystemExit("block %d: payload %d too large" % (i, size))
        chunks[addr] = b[32:32 + size]

    if not chunks:
        raise SystemExit("no programmable blocks in UF2")

    addrs = sorted(chunks)
    base = addrs[0]
    image = bytearray()
    expect = base
    for a in addrs:
        if a != expect:
            raise SystemExit("non-contiguous UF2: gap at 0x%08x (expected 0x%08x)"
                             % (a, expect))
        image += chunks[a]
        expect = a + len(chunks[a])
    return base, bytes(image)


def main():
    path = sys.argv[1]
    dry = "--dry-run" in sys.argv

    base, image = parse_uf2(path)
    print("UF2:        %s" % path)
    print("base addr:  0x%08x" % base)
    print("image size: %d bytes (%.1f KB)" % (len(image), len(image) / 1024.0))
    print("end addr:   0x%08x" % (base + len(image)))

    if base < FLASH_BASE or base % SECTOR_SIZE:
        raise SystemExit("base 0x%08x is not a sector-aligned flash address" % base)

    erase_size = (len(image) + SECTOR_SIZE - 1) // SECTOR_SIZE * SECTOR_SIZE
    padded = image + b"\xFF" * (erase_size - len(image))
    print("erase span: %d bytes (%d sectors)" % (erase_size, erase_size // SECTOR_SIZE))

    if dry:
        print("\nDRY RUN - no hardware touched.")
        return

    pb = Picoboot()
    print("\nconnected: PICOBOOT interface %d" % pb.ifnum)
    pb.reset_interface()
    pb.exclusive_access(EXCLUSIVE_AND_EJECT)
    pb.exit_xip()
    print("exclusive access + exit_xip OK")

    print("erasing %d sectors ..." % (erase_size // SECTOR_SIZE))
    t0 = time.time()
    pb.flash_erase(base, erase_size)
    print("erase done in %.1fs" % (time.time() - t0))

    CHUNK = 4096
    t0 = time.time()
    for off in range(0, len(padded), CHUNK):
        pb.write(base + off, padded[off:off + CHUNK])
        done = min(off + CHUNK, len(padded))
        sys.stdout.write("\rwriting %d/%d bytes (%d%%)"
                         % (done, len(padded), 100 * done // len(padded)))
        sys.stdout.flush()
    print("\nwrite done in %.1fs" % (time.time() - t0))

    print("verifying ...")
    pb.enter_cmd_xip()
    bad = 0
    for off in range(0, len(image), CHUNK):
        want = image[off:off + CHUNK]
        got = pb.read(base + off, len(want))
        if got != want:
            bad += 1
            print("  MISMATCH at 0x%08x" % (base + off))
            if bad > 4:
                break
    if bad:
        pb.close()
        raise SystemExit("VERIFY FAILED - flash does not match the UF2")
    print("verify OK - %d bytes match" % len(image))

    print("rebooting into the application ...")
    pb.reboot(0, 0, 500)
    pb.close()

    for _ in range(30):
        import glob
        ports = glob.glob("/dev/cu.usbmodem*")
        if ports:
            print("SUCCESS - MicroPython is up at %s" % ports[0])
            return
        time.sleep(1)
    print("Flashed and verified, but no serial port appeared yet.")


main()
