"""Tests for converting user commands into wire protocol lines."""

from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import Mock, call, patch

fake_cowsay = types.ModuleType("cowsay")
fake_cowsay.list_cows = lambda: []
sys.modules.setdefault("cowsay", fake_cowsay)

from mood.client.cli import GameClientRunner, run_input_loop


class ClientProtocolMappingTests(unittest.TestCase):
    """Check input-to-protocol transformation with mocked IO."""

    def setUp(self) -> None:
        self.session = Mock()
        self.runner = GameClientRunner(self.session)

    def test_move_two_directions_are_encoded(self) -> None:
        fake_input = Mock(side_effect=["up", "left", EOFError])
        run_input_loop(self.runner, input_func=fake_input)
        self.session.send.assert_has_calls([call("move 0 1"), call("move -1 0")])

    def test_addmon_two_values_are_encoded(self) -> None:
        fake_input = Mock(
            side_effect=[
                'addmon jgsbat hello "first hi" hp 11 coords 2 3',
                'addmon dragon hello "second hi" hp 25 coords 5 1',
                EOFError,
            ]
        )
        run_input_loop(self.runner, input_func=fake_input)
        self.session.send.assert_has_calls(
            [
                call("addmon jgsbat 'first hi' 11 2 3"),
                call("addmon dragon 'second hi' 25 5 1"),
            ]
        )

    def test_addmon_invalid_params_do_not_send(self) -> None:
        fake_input = Mock(side_effect=['addmon jgsbat hello "bad" hp -1 coords 1 1', EOFError])
        with patch("builtins.print") as print_mock:
            run_input_loop(self.runner, input_func=fake_input)
        self.session.send.assert_not_called()
        print_mock.assert_called_with("Invalid command")


if __name__ == "__main__":
    unittest.main()
