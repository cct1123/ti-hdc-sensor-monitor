# HDC3020EVM interface contract

## Authoritative references

- [HDC3020EVM page](https://www.ti.com/tool/HDC3020EVM)
- [EVM user guide SNAU267A](https://www.ti.com/lit/pdf/snau267), sections 1 and 3:
  onboard MSP430F5528, stock 7-bit address 0x44, USB-powered 3.3 V sensor supply.
- [HDC302x datasheet SNAS778D](https://www.ti.com/lit/gpn/hdc3020), tables 6-5/7-1/7-4,
  sections 7.5.7.2/3/6/7/8/9: commands, conversion times, CRC, status, heater and NIST ID.
- [TI HDC3020 GUI v1.0.7 main.js](https://dev.ti.com/gallery/view/THSApps/HDC3020EVM/ver/1.0.7/app/main.js):
  `HDC3Read`, `HDC3Write`, `crcHDC3`, `convT`, `convR`, frequency controls.
- [GUI Composer 1.17 USB2ANY codec](https://dev.ti.com/gallery/view/THSApps/HDC3020EVM/ver/1.0.7/components/gc/1.17/ti-core-databind/src/internal/reg/USB2ANY.js).
- [TMP monitor HID implementation](https://github.com/cct1123/ti-tmp-sensor-monitor/blob/b8e1e4e7116943c826d3b59626059cd2b6d15923/tmpsensor/usb_hid.py),
  reused bridge envelope; its TMP hardware evidence does not validate this HDC board.

References inspected 2026-09-20 and the EVM schematic/USB2ANY error table
rechecked 2026-09-23 after the first physical result. TI GUI source is reference
material, not bundled runtime code.

## USB2ANY

HID VID/PID `2047:0301`, report ID `3F`, 64-byte reports. The VID/PID and
USB2ANY/OneDemo product string were confirmed on the connected EVM (E012).
Reports contain ID, packet length, and an 8-byte header followed by up to 54 payload
bytes. Packet header: `54 CRC payload_length type flags sequence status command`.
Bridge CRC uses polynomial `07`, init `00`, over the packet from payload-length
through payload (excluding report padding). Commands use type 1; replies type 2;
type 3 is an error. Async packets and stale sequences are skipped within a 1 s deadline.
Sequence numbers wrap 254 -> 1. No firmware update or power-switch command is issued.

| Operation | Bridge command | Payload |
| --- | --- | --- |
| Firmware version | `0A` | four zero bytes; expect four version bytes |
| I2C configuration | `01` | `speed, 0, 0` (7-bit, bridge pullups off; 0=100 kHz, 1=400 kHz) |
| Raw I2C write | `02` | `0, address, count, bytes...` |
| Raw I2C read | `03` | `0, address, count, 0` |

The fourth read-payload zero follows TI's HDC-specific `HDC3Read`, although the
generic USB2ANY wrapper uses three payload bytes. Reads return exactly the requested
payload count; short responses fail. Sensor commands are two-byte big endian,
not the TMP sensor's one-byte register address. Separate write/STOP, wait, and
raw read transactions follow TI's HDC GUI path. No clock stretching is required.
The stock EVM has four 10 kΩ I2C pullups tied to its USB-powered 3.3 V rail
(SNAU267A schematic, p. 16). The bridge's own pullups require a distinct 3.3 V
EXT output; leaving them on caused USB2ANY error -54 on the first physical write
(E012). This transport disables bridge pullups for the stock EVM.

## Sensor commands

| Action | LPM0 | LPM1 | LPM2 | LPM3 |
| --- | --- | --- | --- | --- |
| On demand | `2400` | `240B` | `2416` | `24FF` |
| Auto 1 Hz | `2130` | `2126` | `212D` | `21FF` |
| Auto 0.5 Hz | `2032` | `2024` | `202F` | `20FF` |

On-demand waits 16/10/7/6 ms respectively, exceeding datasheet maxima
14.1/8.4/5.7/4.2 ms. Read six bytes: T MSB, T LSB, T CRC, RH MSB, RH LSB, RH CRC.
Both CRCs must pass. Sensor CRC polynomial `31`, initial `FF`, no reflection/final
XOR; TI vector `AB CD -> 6F`. Temperature = `-45 + 175 * raw / 65535` °C;
RH = `100 * raw / 65535` %RH. Values are not clamped to conceal errors.

Auto fetch `E000`; exit auto `3093`. Empty auto-latch all-FF results (including
CRC-protected FFFF words) are discarded as not ready. Auto 1 Hz/0.5 Hz fetch intervals
are at least 1.02/2.02 s. Higher auto rates are deliberately omitted per TI's
self-heating recommendation of no faster than one measurement per second.

Status `F32D`, clear tracking/reset flags `3041`, soft reset `30A2` (20 ms wait).
Status bit 13 indicates heater enabled. Heater off `3066`, on `306D`, configuration
`306E` + CRC-protected word, checked by readback. UI uses only `0001`, a minimum
heater element, with a five-second host timer. One attended physical pulse lasted
5.047 s with status-on/off and a transient temperature rise (E033); heater
current and calibrated thermal behavior were not measured.

Manufacturer `3781` returns `3000` with CRC. NIST serial is three CRC-protected
words read with `3683`, `3684`, `3685`, joined MSB first into a 48-bit hex string.
Manufacturer identity alone does not uniquely prove the HDC3020 model; matching
hardware, NIST responses and actual measurements remain part of physical validation.

USB2ANY `-49` means an I²C write timeout in [TI's USB2ANY SDK API reference](https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/196/0116.API-Reference-for-USB2ANY-SDK-2.8.pdf).
With no USB serial, the transport selects a bridge only when HID enumeration
returns exactly one. It cannot infer which connected bridge carries an HDC3020.
At the HID layer, [HIDAPI specifies](https://github.com/libusb/hidapi/blob/master/hidapi/hidapi.h)
that `hid_write` returns `-1` on error; that return alone does not identify the
physical cause. The transport includes HIDAPI's native error text when available.
