"""TCP session handling and command dispatch for MOOD.

This module defines the asyncio :class:`MudServer`, player :class:`Session`
records, and the wire-protocol handlers that bridge clients to
:class:`~mood.common.engine.Dungeon` game state.
"""

from __future__ import annotations

import asyncio
import shlex
from dataclasses import dataclass

from mood.common.engine import Dungeon, Monster, MonsterSpec


@dataclass(slots=True)
class Session:
    """Logged-in player with outbound stream and dungeon coordinates."""

    name: str
    writer: asyncio.StreamWriter
    pos: tuple[int, int] = (0, 0)


class MudServer:
    """Game server with named sessions, broadcast chat, and wandering monsters.

    The server accepts a ``login <name>`` line, then newline-framed commands
    (``move``, ``addmon``, ``attack``, ``sayall``). Optional background task
    moves one random monster every 30 seconds when enabled.
    """

    def __init__(self, *, wandering_monsters: bool = True) -> None:
        """Create an empty server with a fresh dungeon.

        Args:
            wandering_monsters: When ``True``, start periodic random monster moves.
        """
        self._game = Dungeon()
        self._sessions: dict[str, Session] = {}
        self._wandering_monsters = wandering_monsters

    async def run_wandering_monsters(self) -> None:
        """Sleep 30s, then every 30s move one monster and notify players.

        If no legal move exists, the tick does nothing. After a move,
        players standing on the destination cell receive the same encounter
        line as if they had stepped onto that monster.
        """
        await asyncio.sleep(30)
        while True:
            if self._wandering_monsters:
                result = self._game.wander_random_monster()
                if result is not None:
                    name, direction, pos = result
                    self.broadcast(f"{name} moved one cell {direction}")
                    cell = self._game[pos]
                    if isinstance(cell, Monster):
                        for sess in self._sessions.values():
                            if sess.pos == pos:
                                self.send_to(
                                    sess.name,
                                    self._render_monster(cell.name, cell.hello),
                                )
            await asyncio.sleep(30)

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Accept a login line, then process commands until disconnect.

        Args:
            reader: Inbound byte stream from the client.
            writer: Outbound stream for line-oriented replies.
        """
        name: str | None = None
        try:
            raw = await reader.readline()
            if not raw:
                return
            line = raw.decode().strip()
            parts = shlex.split(line)
            if len(parts) != 2 or parts[0] != "login":
                await self._send(writer, "Protocol error: expected 'login <name>'")
                return
            candidate = parts[1]
            if not candidate or any(ch.isspace() for ch in candidate):
                await self._send(writer, "Login rejected: invalid username")
                return
            if candidate in self._sessions:
                await self._send(writer, f"Login rejected: username '{candidate}' is busy")
                return

            name = candidate
            self._sessions[name] = Session(name=name, writer=writer)
            await self._send(writer, f"Login accepted: {name}")
            self.broadcast(f"{name} entered MUD")

            while True:
                raw = await reader.readline()
                if not raw:
                    return
                line = raw.decode().strip()
                if not line:
                    continue
                await self._handle_command(name, line)
        finally:
            if name is not None and name in self._sessions:
                del self._sessions[name]
                self.broadcast(f"{name} left MUD")
            writer.close()
            await writer.wait_closed()

    async def _handle_command(self, username: str, line: str) -> None:
        """Parse one client line and mutate game state or reply with an error.

        Args:
            username: Sender of ``line``.
            line: Single logical command (possibly quoted tokens).
        """
        sess = self._sessions.get(username)
        if sess is None:
            return
        try:
            parts = shlex.split(line)
            if not parts:
                return
            cmd = parts[0]
            if cmd == "move":
                dx, dy = int(parts[1]), int(parts[2])
                sess.pos, encounter = self._game.move(sess.pos, dx, dy)
                self.send_to(username, f"Moved to ({sess.pos[0]}, {sess.pos[1]})")
                if encounter is not None:
                    self.send_to(
                        username,
                        self._render_monster(encounter["name"], encounter["hello"]),
                    )
                return

            if cmd == "addmon":
                _, mon_name, hello, hp_s, xs, ys = parts
                hp, x, y = int(hp_s), int(xs), int(ys)
                self._game.place_monster(x, y, MonsterSpec(mon_name, hello, hp))
                self.broadcast(
                    f"{username} set monster {mon_name} with {hp} hp at ({x}, {y})"
                )
                return

            if cmd == "attack":
                _, target, dmg_s, weapon = parts
                damage = int(dmg_s)
                mon_name: str | None = None if target == "*" else target
                result = self._game.attack(sess.pos, mon_name, damage)
                if not result["ok"]:
                    why = result["why"]
                    if why == "empty":
                        self.send_to(username, "No monster here")
                    else:
                        self.send_to(username, f"No {result['name']} here")
                    return

                mon = str(result["name"])
                dealt = int(result["dealt"])
                left = int(result["left"])
                if left == 0:
                    self.broadcast(
                        f"{username} attacked {mon} with {weapon}: "
                        f"dealt {dealt}, {mon} died"
                    )
                else:
                    self.broadcast(
                        f"{username} attacked {mon} with {weapon}: "
                        f"dealt {dealt}, hp left {left}"
                    )
                return

            if cmd == "sayall":
                if len(parts) != 2:
                    self.send_to(username, "Invalid command")
                    return
                message = parts[1]
                self.broadcast(f"{username}: {message}")
                return

            if cmd == "movemonsters":
                if len(parts) != 2 or parts[1] not in {"on", "off"}:
                    self.send_to(username, "Invalid command")
                    return
                self._wandering_monsters = parts[1] == "on"
                state = "on" if self._wandering_monsters else "off"
                self.send_to(username, f"Moving monsters: {state}")
                return

            self.send_to(username, f"Unknown command: {cmd}")
        except (ValueError, IndexError):
            self.send_to(username, "Invalid command")

    def broadcast(self, text: str) -> None:
        """Send ``text`` as a line to every connected session.

        Args:
            text: Payload without the trailing newline (added when writing).
        """
        for sess in self._sessions.values():
            self._send_async(sess.writer, text)

    def send_to(self, username: str, text: str) -> None:
        """Send ``text`` as a line to ``username`` only.

        Args:
            username: Target session name.
            text: Payload without the trailing newline.
        """
        sess = self._sessions.get(username)
        if sess is None:
            return
        self._send_async(sess.writer, text)

    async def _send(self, writer: asyncio.StreamWriter, text: str) -> None:
        """Write ``text``\\n and wait for the kernel buffer to drain.

        Args:
            writer: Client stream.
            text: Single logical line of UTF-8 text.
        """
        writer.write((text + "\n").encode())
        await writer.drain()

    def _send_async(self, writer: asyncio.StreamWriter, text: str) -> None:
        """Schedule :meth:`_send` without blocking the caller.

        Args:
            writer: Client stream.
            text: Single logical line of UTF-8 text.
        """
        asyncio.create_task(self._send(writer, text))

    def _render_monster(self, name: str, hello: str) -> str:
        """Format a monster encounter line for a player.

        Args:
            name: Monster name.
            hello: Greeting string stored in the monster spec.

        Returns:
            One-line human-readable encounter text.
        """
        return f"{name} says: {hello}"
