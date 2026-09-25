import sys
import types
import unittest
from unittest.mock import Mock, patch

from hdcsensor.errors import SensorError
from hdcsensor.usb_hid import USB2ANYHIDTransport, _crc8


def reply(sequence, command, payload=b"", kind=2, status=0):
    packet = bytearray([0x54, 0, len(payload), kind, 0, sequence, status, command])
    packet.extend(payload)
    packet[1] = _crc8(packet[2:])
    return (bytes([0x3F, len(packet)]) + packet).ljust(64, b"\xa5")


class FakeHID:
    def __init__(self):
        self.pending = []
        self.writes = []
        self.closed = False
        self.read_data = b"\xab\xcd\x6f"

    def open_path(self, path):
        self.path = path
        self.closed = False

    def write(self, report):
        self.writes.append(bytes(report))
        command = report[9]
        payload = bytes([2, 7, 0, 16]) if command == 10 else self.read_data if command == 3 else b""
        self.pending.append(reply(report[7], command, payload))
        return 64

    def read(self, size, timeout):
        return self.pending.pop(0) if self.pending else []

    def close(self):
        self.closed = True


class HIDTests(unittest.TestCase):
    def setUp(self):
        self.device = FakeHID()
        self.hid = types.SimpleNamespace(
            enumerate=Mock(return_value=[{"path": b"test", "serial_number": "TEST"}]),
            device=Mock(return_value=self.device),
        )
        patcher = patch.dict(sys.modules, {"hid": self.hid})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.transport = USB2ANYHIDTransport()
        self.addCleanup(self.transport.close)

    def test_bridge_crc_known_vectors(self):
        self.assertEqual(_crc8(b"123456789"), 0xF4)
        # Captured TMP bridge packets from the reference app: same USB2ANY framing.
        self.assertEqual(_crc8(bytes.fromhex("04 01 00 ad 00 0a 00 00 00 00")), 0x68)
        self.assertEqual(_crc8(bytes.fromhex("04 02 00 ad 00 0a 02 07 00 10")), 0xA9)

    def test_raw_framing_matches_ti_hdc_gui(self):
        self.transport.open()
        self.transport.write(b"\x24\x00")
        self.assertEqual(self.transport.read(3), b"\xab\xcd\x6f")
        self.assertEqual(self.device.writes[1][9:13], bytes([1, 0, 0, 0]))
        self.assertEqual(self.device.writes[2][9:15], bytes([2, 0, 0x44, 2, 0x24, 0]))
        self.assertEqual(self.device.writes[3][9:14], bytes([3, 0, 0x44, 3, 0]))
        self.assertEqual(self.transport.firmware_version, "2.7.0.16")
        self.hid.enumerate.assert_called_once_with(0x2047, 0x0301)
        for report in self.device.writes:
            self.assertEqual(len(report), 64)
            self.assertEqual(report[3], _crc8(report[4 : 2 + report[1]]))

    def test_missing_ambiguous_and_serial_selection(self):
        for devices in ([], [{}, {}]):
            self.hid.enumerate.return_value = devices
            with self.assertRaises(SensorError):
                self.transport.open()
        self.hid.device.assert_not_called()
        self.hid.enumerate.return_value = [
            {"path": b"a", "serial_number": "A"},
            {"path": b"b", "serial_number": "B"},
        ]
        self.transport.serial_number = "B"
        self.transport.open()
        self.assertEqual(self.device.path, b"b")

    def test_blank_serial_lists_bridges_without_opening_either(self):
        self.hid.enumerate.return_value = [
            {"path": b"a", "serial_number": "47F3A26E27001D00"},
            {"path": b"b", "serial_number": "87F2A26E08002500"},
        ]
        with self.assertRaisesRegex(SensorError, "47F3A26E27001D00.*87F2A26E08002500"):
            self.transport.open()
        self.hid.device.assert_not_called()
        self.assertEqual(self.device.writes, [])

    def test_i2c_write_timeout_identifies_selected_bridge(self):
        self.transport.open()
        self.device.pending.append(reply(3, 2, kind=3, status=207))
        with self.assertRaisesRegex(SensorError, "serial TEST command 0x02: I2C write timed out \\(-49\\)"):
            self.transport.write(b"\x37\x81")

    def test_truncated_corrupt_and_short_responses(self):
        self.transport.open()
        for response, message in (
            (b"\x3f", "header"),
            (b"\x3f\x3f" + bytes(62), "length"),
            (reply(3, 3)[:3] + b"\xff" + reply(3, 3)[4:], "CRC"),
        ):
            with (
                patch.object(self.device, "read", return_value=response),
                self.assertRaisesRegex(SensorError, message),
            ):
                self.transport.read(3)
        self.device.pending.clear()
        self.device.read_data = b"\x00"
        with self.assertRaisesRegex(SensorError, "expected 3"):
            self.transport.read(3)

    def test_nak_timeout_short_write_and_unplug(self):
        self.transport.open()
        self.device.pending.append(reply(3, 3, kind=3, status=212))
        with self.assertRaisesRegex(SensorError, "not acknowledged"):
            self.transport.read(3)
        self.device.pending.append(reply(4, 3, kind=3, status=202))
        with self.assertRaisesRegex(SensorError, "3.3 V EXT power"):
            self.transport.read(3)
        self.transport.timeout_s = 0.001
        with (
            patch.object(self.device, "read", return_value=[]),
            self.assertRaisesRegex(SensorError, "timed out"),
        ):
            self.transport.read(3)
        with (
            patch.object(self.device, "write", return_value=0),
            self.assertRaisesRegex(SensorError, "wrote 0"),
        ):
            self.transport.read(3)
        with (
            patch.object(self.device, "write", side_effect=OSError("unplugged")),
            self.assertRaisesRegex(SensorError, "unplugged"),
        ):
            self.transport.read(3)

    def test_stale_async_replies_wrap_and_reopen(self):
        self.transport.open()
        self.device.pending.extend([reply(1, 3), reply(3, 10), reply(3, 3, kind=5)])
        self.assertEqual(self.transport.read(3), b"\xab\xcd\x6f")
        for _ in range(260):
            self.transport.read(3)
        self.assertTrue(all(1 <= report[7] <= 254 for report in self.device.writes))
        self.assertEqual(self.device.writes[254][7], 1)
        self.transport.close()
        self.transport.close()
        self.transport.open()
        self.assertEqual(self.device.writes[-2][7], 1)

    def test_input_validation_before_io(self):
        for count in (0, 55, True, 1.5):
            with self.assertRaises(ValueError):
                self.transport.read(count)
        for value in (b"", bytes(52)):
            with self.assertRaises(ValueError):
                self.transport.write(value)
        for address in (0x43, 0x48, True, 68.0):
            with self.assertRaises(ValueError):
                USB2ANYHIDTransport(address)
        self.hid.enumerate.assert_not_called()

    def test_real_driver_over_fake_hid_bridge(self):
        from hdcsensor.sensors import HDC3020Sensor
        from hdcsensor.simulation import SimulatedTransport

        board = SimulatedTransport()
        board.open()

        def bridge_write(report):
            command = report[9]
            if command == 2:
                board.write(bytes(report[13 : 13 + report[12]]))
            elif command == 3:
                self.device.read_data = board.read(report[12])
            return original(report)

        original = self.device.write
        with patch.object(self.device, "write", side_effect=bridge_write):
            sensor = HDC3020Sensor(self.transport)
            try:
                sensor.open()
                sample = sensor.read_measurement()
                self.assertEqual(sensor.identity.nist_id, "0123456789AB")
                self.assertTrue(20 < sample.temperature_c < 26)
                self.assertTrue(40 < sample.relative_humidity_pct < 50)
                self.assertEqual(self.device.writes[-3][9:14], bytes([3, 0, 0x44, 6, 0]))
            finally:
                sensor.close()
        self.assertTrue(self.device.closed)
