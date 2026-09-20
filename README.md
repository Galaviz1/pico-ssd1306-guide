# pico-ssd1306-guide

Driving an SSD1306 128×32 OLED from a Raspberry Pi Pico over I²C — wiring, driver, demos, and the diagnostics that got a stubborn board working.

This started as "check if the OLED works" and turned up three separate problems worth writing down. If you are hitting any of them, the fixes are below.

---

## Demo

The blinking text running on the hardware described here:

<a href="https://www.youtube.com/shorts/pYQEHXCuiMY">
  <img src="https://img.youtube.com/vi/pYQEHXCuiMY/hqdefault.jpg" alt="SSD1306 OLED blinking text on a Raspberry Pi Pico" width="260">
</a>

[youtube.com/shorts/pYQEHXCuiMY](https://www.youtube.com/shorts/pYQEHXCuiMY)

---

## Wiring

| OLED pin | Pico physical pin | Pico label | Carries |
| --- | --- | --- | --- |
| `SDA` | **1** | `GP0` | I²C data |
| `SCL` | **2** | `GP1` | I²C clock |
| `GND` | **3** | `GND` | 0 V reference |
| `VCC` / `VDD` | **36** | `3V3(OUT)` | 3.3 V power |

Pins 1, 2 and 3 are the three pads nearest the USB connector, so only the power wire is long.

> **Power from pin 36, not pin 40.** Pin 40 is `VBUS` — raw 5 V from USB. Many SSD1306 modules tolerate 5 V on `VCC`, but their pull-up resistors then hold SDA and SCL at 5 V, outside the RP2040's input spec.

> **Read the silkscreen.** The 4-pin header ships in several orders — `GND VCC SCL SDA` and `VCC GND SDA SCL` are both common. Match by printed label, never by position.

**[→ Read the illustrated wiring guide](https://galaviz1.github.io/pico-ssd1306-guide/)** — schematic, step-by-step, and the I²C bus diagram. Source: [`docs/wiring.html`](docs/wiring.html).

---

## Quick start

```bash
pip3 install --user mpremote

# confirm the display answers on the bus (expects ['0x3c'])
python3 -m mpremote connect auto run scan.py

# copy the driver onto the board, once
python3 -m mpremote connect auto cp ssd1306.py :

# blinking text
python3 -m mpremote connect auto run oled_demo.py
```

In VS Code, press <kbd>⇧</kbd><kbd>⌘</kbd><kbd>B</kbd> to run the open file on the Pico. `.vscode/tasks.json` also provides *Copy file to Pico*, *List files on Pico* and *Open Pico REPL*.

The ▶ Run button will **not** work — it runs files with your desktop Python, which has no `machine` module. `oled_demo.py` detects this and prints instructions instead of a traceback.

---

## Three things that were wrong

### 1. Use `SoftI2C`, not hardware `I2C`

On the board this was developed against, the RP2040's hardware I²C block does not work with this display. It finds the device during a scan, then NAKs every data byte — identically at 400 kHz and at 20 kHz. It also falsely ACKs address `0x3D`, where nothing is connected.

| | hardware `I2C(0)` | `SoftI2C` |
| --- | --- | --- |
| scan finds `0x3C` | yes | yes |
| write data bytes | **every one NAKs** | works |
| probe empty `0x3D` | **falsely ACKs** | correctly `ENODEV` |

```python
from machine import Pin, SoftI2C
i2c = SoftI2C(sda=Pin(0), scl=Pin(1), freq=400_000)
```

Reproduce with `diagnostics/i2c_diag2.py`, which walks each transfer phase on both implementations. `diagnostics/i2c_diag.py` sweeps the bus speed and reads the idle line levels — both lines idle high confirms the module's pull-ups are working and it has power.

### 2. Drag-and-drop flashing is broken on recent macOS

Copying a `.uf2` to `/Volumes/RPI-RP2` silently does nothing on macOS builds that mount it through **FSKit** (check with `mount | grep RPI-RP2`). The copy reports success and free space drops, but the bootloader never sees the file — the RP2 bootrom serves a read-only virtual FAT, so the cached writes are simply discarded. Listing the volume afterwards shows the file was never there.

`tools/pb_flash.py` works around this entirely by speaking **PICOBOOT** to the bootrom over USB interface 1, which macOS does not claim. **No root required.**

```bash
brew install libusb          # or: apt install libusb-1.0-0
pip3 install --user pyusb

python3 tools/pb_flash.py --dry-run   # parse and validate the UF2, touch no hardware
python3 tools/pb_flash.py             # erase, write, verify every byte
```

It refuses non-contiguous images and wrong-family UF2s, and reads the whole image back to confirm the write.

### 3. A stuck BOOTSEL button looks exactly like a dead board

If the board enters the bootloader on every reset no matter what you flash, check the button before you suspect the firmware:

```python
import rp2
print(rp2.bootsel_button())   # constant 1 = stuck pressed
```

The bootrom samples that line at every reset. Stuck pressed means it never boots your code, while flash reads and writes still work perfectly — so the board looks blank while being entirely healthy.

`tools/check_boot2.py` settles the question from the other side: it reads the first 256 bytes out of flash and verifies the boot2 CRC (CRC-32/MPEG-2) plus the application vector table. A valid checksum with sane SP and PC means the image *would* boot, so the fault is the button.

**Working around it:** `./start.sh` boots the board anyway. It stages boot2 into SRAM and executes it with `LR = 0`, which is how the bootrom enters it — the standard RP2040 boot2 checks `LR` and vectors into flash only when it is zero, otherwise returning to its caller. A plain `PC_EXEC` call therefore configures XIP and politely returns; a 12-byte Thumb stub that zeroes `LR` first makes it boot properly.

---

## Board report

`board_info.py` reports what a board actually is, measured rather than assumed — useful when you are not sure which RP2040 variant you have, how much flash is left, or whether BOOTSEL is stuck.

```bash
python3 -m mpremote connect auto run board_info.py
```

From the unit this repo was developed against:

```
[identity]
  board       : Raspberry Pi Pico with RP2040
  unique id   : E660C0D1C7385A21
  build       : RPI_PICO
  micropython : 1.29.0

[clock]
  system      : 125000000 Hz (125 MHz)

[ram]
  heap free   : 221.3 KB
  heap used   : 6.9 KB
  heap total  : 228.3 KB

[flash]
  total       : 2048.0 KB
  firmware    : 640.0 KB region
  filesystem  : 1408.0 KB total, 1392.0 KB free, 16.0 KB used

[temperature]
  on-die      : 19.1 C

[bootsel]
  button      : PRESSED
  WARNING: reads pressed with nobody touching it.
```

That last line is finding 3 showing up in one command. `rp2.bootsel_button()` returning `1` while nobody is touching the board means the bootrom will enter the bootloader at every reset.

### RP2040 reference

| | |
| --- | --- |
| CPU | Dual-core Arm Cortex-M0+, up to 133 MHz |
| SRAM | 264 KB on-chip |
| Flash | 2 MB QSPI, external |
| GPIO | 26 exposed (`GP0`–`GP22`, `GP26`–`GP28`) |
| ADC | 4 × 12-bit inputs, plus an internal temperature sensor on channel 4 |
| Interfaces | 2 × UART, 2 × SPI, 2 × I²C, 16 × PWM |
| PIO | 2 blocks, 4 state machines each |
| Power | 1.8–5.5 V in; `3V3(OUT)` on pin 36 sources roughly 300 mA |

The heap reads ~228 KB against 264 KB of physical SRAM — the difference is MicroPython's static allocations and stack, not missing memory.

---

## Layout

```
oled_demo.py          blinking text (runs on the Pico)
oled_test.py          five-stage display self-test
scan.py               I²C scan across five common pin pairs
board_info.py         measured board report: clock, RAM, flash, temp, BOOTSEL
ssd1306.py            display driver (micropython-lib, MIT)

diagnostics/
  i2c_diag.py         bus-speed sweep + idle line levels
  i2c_diag2.py        per-phase comparison of hardware I2C vs SoftI2C

tools/                host-side, run with desktop Python
  picoboot.py         PICOBOOT driver for the RP2040 bootrom
  pb_flash.py         flash a UF2 over USB, no root
  pb_test.py          zero-risk PICOBOOT connectivity check
  probe.py            dump the bootloader's USB descriptors
  check_boot2.py      verify boot2 CRC + app vector table in flash
  boot2_jump.py       boot into flash past a stuck BOOTSEL button
  boot2_run.py        execute boot2 (returns to the bootrom; see finding 3)
  boot_app.py         jump straight to the app entry, skipping boot2
  reboot_app.py       plain PICOBOOT reboot
  detect.sh           report which mode the board is in
  flash.sh            raw block-device flash (needs sudo; prefer pb_flash.py)

docs/wiring.html      illustrated wiring guide with schematic
start.sh              boot the board past a stuck BOOTSEL button
```

Firmware `.uf2` files are **not** committed. Download one from
[micropython.org/download/RPI_PICO](https://micropython.org/download/RPI_PICO/) and drop it in the repo root; the tools find `RPI_PICO-*.uf2` automatically, or take a path as an argument.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Scan returns `[]` | SDA/SCL swapped, or a wire not seated | Swap the two data wires and rescan — fastest test, and harmless |
| Scan finds `0x3C`, then `OSError: [Errno 5] EIO` | Hardware I²C block | Switch to `SoftI2C` (finding 1) |
| Display dark, scan fine | Wrong geometry | Try `SSD1306_I2C(128, 64, ...)` |
| Image shifted or doubled | It is an SH1106, not an SSD1306 | Use an SH1106 driver (2-pixel column offset) |
| Brief flash then nothing | Power on `VBUS`, or a brownout | Move `VCC` to pin 36; check the ground wire |
| No serial port at all | No firmware, or stuck BOOTSEL | `tools/detect.sh`, then finding 3 |
| `ModuleNotFoundError: No module named 'machine'` | Ran the file on your computer | It runs on the Pico — use <kbd>⇧</kbd><kbd>⌘</kbd><kbd>B</kbd> or `mpremote ... run` |
| UF2 copy to `RPI-RP2` does nothing | FSKit mount | Use `tools/pb_flash.py` (finding 2) |

---

## Tested against

Raspberry Pi Pico (RP2040, USB `2e8a:0003`) · MicroPython v1.29.0 · 0.91″ SSD1306 128×32 at `0x3C` · macOS 14.8.9 · Python 3.7

## License

MIT — see [LICENSE](LICENSE). `ssd1306.py` is from
[micropython-lib](https://github.com/micropython/micropython-lib), also MIT.
