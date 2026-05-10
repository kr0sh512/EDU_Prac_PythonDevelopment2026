"""Integration tests for client-to-server command handling."""

from __future__ import annotations

import multiprocessing
import socket
import time
import unittest

from mood.server import run_server


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


class ServerCommandFlowTests(unittest.TestCase):
    """Check protocol command processing on live server."""

    def setUp(self) -> None:
        self.port = _get_free_port()
        self.proc = multiprocessing.Process(
            target=run_server,
            kwargs={"host": "127.0.0.1", "port": self.port, "wandering_monsters": False},
        )
        self.proc.start()
        self.sock = self._connect_with_retry()
        self.file = self.sock.makefile("rwb", buffering=0)
        self._send("login tester")
        self._expect_line_contains("Login accepted:")
        self._expect_line_contains("entered MUD")

    def tearDown(self) -> None:
        try:
            self.file.close()
            self.sock.close()
        finally:
            self.proc.terminate()
            self.proc.join(timeout=2)

    def _connect_with_retry(self) -> socket.socket:
        deadline = time.time() + 3
        while True:
            try:
                sock = socket.create_connection(("127.0.0.1", self.port), timeout=1.0)
                sock.settimeout(1.0)
                return sock
            except OSError:
                if time.time() >= deadline:
                    raise
                time.sleep(0.05)

    def _send(self, line: str) -> None:
        self.file.write((line + "\n").encode())

    def _read_line(self) -> str:
        raw = self.file.readline()
        if not raw:
            self.fail("Server closed connection unexpectedly")
        return raw.decode().strip()

    def _expect_line_contains(self, text: str, timeout: float = 2.0) -> str:
        deadline = time.time() + timeout
        while time.time() < deadline:
            line = self._read_line()
            if text in line:
                return line
        self.fail(f"Response containing {text!r} not received")

    def test_set_monster_command(self) -> None:
        self._send('addmon jgsbat "hello" 12 1 0')
        self._expect_line_contains("set monster jgsbat")

    def test_move_to_monster_gets_greeting(self) -> None:
        self._send('addmon jgsbat "hello" 12 1 0')
        self._expect_line_contains("set monster jgsbat")
        self._send("move 1 0")
        self._expect_line_contains("Moved to (1, 0)")
        self._expect_line_contains("jgsbat says: hello")

    def test_attack_monster_command(self) -> None:
        self._send('addmon jgsbat "hello" 12 1 0')
        self._expect_line_contains("set monster jgsbat")
        self._send("move 1 0")
        self._expect_line_contains("jgsbat says: hello")
        self._send("attack * 10 sword")
        self._expect_line_contains("attacked jgsbat with sword")


if __name__ == "__main__":
    unittest.main()
