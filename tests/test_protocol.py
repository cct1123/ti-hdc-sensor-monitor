import unittest

from hdcsensor.errors import CRCError, NotReadyError, SensorError
from hdcsensor.protocol import (
    crc8,
    decode_measurement,
    decode_word,
    encode_word,
    validate_interval,
    validate_settings,
)


class ProtocolTests(unittest.TestCase):
    def test_ti_crc_vectors(self):
        for data, expected in ((b"\xab\xcd", 0x6F), (b"\x3f\xff", 0x06), (b"\x00\x9f", 0x96)):
            self.assertEqual(crc8(data), expected)
        self.assertEqual(encode_word(0xABCD), b"\xab\xcd\x6f")

    def test_conversion_endpoints_and_midpoint(self):
        for raw, t, rh in ((0, -45, 0), (65535, 130, 100), (32768, 42.501335, 50.000763)):
            value = decode_measurement(encode_word(raw) * 2)
            self.assertAlmostEqual(value.temperature_c, t, places=5)
            self.assertAlmostEqual(value.relative_humidity_pct, rh, places=5)

    def test_both_crc_words_required_and_truncation_rejected(self):
        packet = encode_word(25000) + encode_word(30000)
        for position in range(6):
            corrupt = bytearray(packet)
            corrupt[position] ^= 1
            with self.assertRaises(CRCError):
                decode_measurement(corrupt)
        for length in (0, 2, 3, 5, 7):
            with self.assertRaises(SensorError):
                decode_measurement(bytes(length))
        with self.assertRaises(SensorError):
            decode_word(b"\x00\x00")

    def test_empty_auto_readouts_are_not_samples(self):
        for packet in (b"\xff" * 6, encode_word(65535) * 2):
            with self.assertRaises(NotReadyError):
                decode_measurement(packet, auto=True)

    def test_validation_rejects_nonfinite_and_invalid_inputs(self):
        for value in (0, 0.9, 61, float("nan"), float("inf"), None, True):
            with self.assertRaises(ValueError):
                validate_interval(value)
        for mode, lp in (("bad", 0), ("on_demand", -1), ("auto_1hz", True), ("on_demand", 1.5)):
            with self.assertRaises(ValueError):
                validate_settings(mode, lp)
