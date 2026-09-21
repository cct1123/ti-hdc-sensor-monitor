import unittest
from unittest.mock import patch

from hdcsensor.errors import NotReadyError
from hdcsensor.protocol import Command, decode_measurement
from hdcsensor.simulation import SimulatedTransport


class SimulationTimingTests(unittest.TestCase):
    def test_late_fetch_does_not_shift_autonomous_conversion_clock(self):
        board = SimulatedTransport()
        board.open()
        with patch("hdcsensor.simulation.time.monotonic", return_value=0):
            board.write(bytes.fromhex("21 30"))
        for now in (1.7, 2.1, 4.2):
            with patch("hdcsensor.simulation.time.monotonic", return_value=now):
                board.write(Command.FETCH.to_bytes(2, "big"))
                decode_measurement(board.read(6), auto=True)
        with patch("hdcsensor.simulation.time.monotonic", return_value=4.5):
            board.write(Command.FETCH.to_bytes(2, "big"))
            with self.assertRaises(NotReadyError):
                decode_measurement(board.read(6), auto=True)
