import unittest
from unittest.mock import Mock, patch

from hdcsensor.errors import SensorError
from hdcsensor.protocol import Command, encode_word
from hdcsensor.sensors import HDC3020Sensor
from hdcsensor.simulation import SimulatedTransport


class SensorTests(unittest.TestCase):
    def setUp(self):
        self.transport = SimulatedTransport()
        self.transport.write = Mock(wraps=self.transport.write)
        self.sleep = Mock()
        self.sensor = HDC3020Sensor(self.transport, sleep=self.sleep)
        self.sensor.open()
        self.addCleanup(self.sensor.close)

    def test_identity_and_initial_state(self):
        self.assertEqual(self.sensor.identity.manufacturer_id, 0x3000)
        self.assertEqual(self.sensor.identity.nist_id, "0123456789AB")
        self.assertFalse(self.sensor.status_word & 0x2000)
        self.assertEqual(self.sensor.mode, "on_demand")

    def test_fresh_measurement_waits_for_max_conversion(self):
        value = self.sensor.read_measurement()
        self.assertTrue(20 < value.temperature_c < 26)
        self.assertTrue(40 < value.relative_humidity_pct < 50)
        self.sleep.assert_any_call(0.016)
        self.assertIn(((b"\x24\x00",),), [(c.args,) for c in self.transport.write.call_args_list])

    def test_auto_and_low_power_command_mapping(self):
        for lp, command in enumerate((0x2130, 0x2126, 0x212D, 0x21FF)):
            self.sensor.configure("auto_1hz", lp)
            self.assertEqual(self.transport.write.call_args.args[0], command.to_bytes(2, "big"))
        self.sensor.configure("on_demand", 3)
        self.sensor.read_measurement()
        self.sleep.assert_any_call(0.006)

    def test_heater_verified_and_reset_restores_defaults(self):
        self.sensor.set_heater(True)
        self.assertTrue(self.sensor.read_measurement().heater_on)
        self.assertIn(unittest.mock.call(b"\x30\x6e" + encode_word(1)), self.transport.write.call_args_list)
        self.sensor.reset()
        self.assertEqual(self.sensor.low_power, 0)
        self.assertFalse(self.sensor.status_word & 0x2000)
        self.sensor.clear_status()
        self.assertEqual(self.sensor.status_word, 0)

    def test_bad_identity_releases_transport_without_sensor_writes(self):
        transport = Mock(name="WrongDevice", serial_number="wrong", firmware_version="1", address=0x44)
        transport.read.return_value = encode_word(0x1234)
        sensor = HDC3020Sensor(transport)
        with self.assertRaisesRegex(SensorError, "manufacturer"):
            sensor.open()
        transport.close.assert_called_once()
        transport.write.assert_called_once_with(b"\x37\x81")

    def test_reopen_rejects_changed_identity_before_volatile_writes(self):
        identity = self.sensor.identity
        self.sensor.close()
        self.transport.write.reset_mock()
        original_read = self.transport.read

        def changed_nist(count):
            if self.transport.pending == Command.NIST_LOW:
                return encode_word(0)
            return original_read(count)

        with (
            patch.object(self.transport, "read", side_effect=changed_nist),
            self.assertRaisesRegex(SensorError, "identity changed"),
        ):
            self.sensor.open(expected_identity=identity)
        self.assertFalse(self.transport.opened)
        commands = [call.args[0][:2] for call in self.transport.write.call_args_list]
        self.assertNotIn(Command.HEATER_OFF.to_bytes(2, "big"), commands)
        self.assertNotIn(Command.EXIT_AUTO.to_bytes(2, "big"), commands)

    def test_cleanup_attempts_both_commands_and_releases_even_on_error(self):
        self.transport.write.side_effect = OSError("unplugged")
        with self.assertRaisesRegex(SensorError, "shutdown"):
            self.sensor.close()
        self.assertFalse(self.transport.opened)
        self.assertEqual(
            self.transport.write.call_args_list[-2:],
            [
                unittest.mock.call(Command.HEATER_OFF.to_bytes(2, "big")),
                unittest.mock.call(Command.EXIT_AUTO.to_bytes(2, "big")),
            ],
        )
