"""TCP session handling and command dispatch for MOOD.

This module defines the asyncio :class:`MudServer`, player :class:`Session`
records, and the wire-protocol handlers that bridge clients to
:class:`~mood.common.engine.Dungeon` game state.
"""

from __future__ import annotations

import asyncio
import gettext
import io
import pathlib
import shlex
from dataclasses import dataclass
from typing import Callable

from babel.messages import mofile, pofile
from mood.common.engine import Dungeon, Monster, MonsterSpec


def _load_ru_translation() -> gettext.NullTranslations | gettext.GNUTranslations:
    base = pathlib.Path(__file__).parent / "locale" / "ru_RU.UTF8" / "LC_MESSAGES"
    po_path = base / "mood_server.po"
    if not po_path.exists():
        return gettext.NullTranslations()
    with po_path.open("r", encoding="utf-8") as po_file:
        catalog = pofile.read_po(po_file, locale="ru_RU")
    mo_bytes = io.BytesIO()
    mofile.write_mo(mo_bytes, catalog)
    mo_bytes.seek(0)
    return gettext.GNUTranslations(mo_bytes)


_RU_TRANSLATION = _load_ru_translation()


@dataclass(slots=True)
class Session:
    """Logged-in player with outbound stream and dungeon coordinates."""

    name: str
    writer: asyncio.StreamWriter
    pos: tuple[int, int] = (0, 0)
    locale: str = "en_US.UTF-8"


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
            self.broadcast_event(lambda tr: tr.gettext("{user} entered MUD").format(user=name))

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
                self.broadcast_event(lambda tr: tr.gettext("{user} left MUD").format(user=name))
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
                self.broadcast_event(
                    lambda tr: tr.gettext(
                        "{user} set monster {monster} with {hp} at ({x}, {y})"
                    ).format(
                        user=username,
                        monster=mon_name,
                        hp=self._hp_phrase(tr, hp),
                        x=x,
                        y=y,
                    )
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
                    self.broadcast_event(
                        lambda tr: tr.gettext(
                            "{user} attacked {monster} with {weapon}: dealt {dealt}, {monster} died"
                        ).format(
                            user=username,
                            monster=mon,
                            weapon=weapon,
                            dealt=self._hp_phrase(tr, dealt),
                        )
                    )
                else:
                    self.broadcast_event(
                        lambda tr: tr.gettext(
                            "{user} attacked {monster} with {weapon}: dealt {dealt}, hp left {left}"
                        ).format(
                            user=username,
                            monster=mon,
                            weapon=weapon,
                            dealt=self._hp_phrase(tr, dealt),
                            left=self._hp_phrase(tr, left),
                        )
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

            if cmd == "locale":
                if len(parts) != 2:
                    self.send_to(username, "Invalid command")
                    return
                sess.locale = parts[1]
                self.send_to_event(
                    username,
                    lambda tr: tr.gettext("Set up locale: {locale}").format(
                        locale=sess.locale
                    ),
                )
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

    def send_to_event(
        self,
        username: str,
        formatter: Callable[[gettext.NullTranslations | gettext.GNUTranslations], str],
    ) -> None:
        """Render an event per-recipient locale and send to one client."""
        sess = self._sessions.get(username)
        if sess is None:
            return
        self._send_async(sess.writer, formatter(self._tr_for(sess.locale)))

    def broadcast_event(
        self,
        formatter: Callable[[gettext.NullTranslations | gettext.GNUTranslations], str],
    ) -> None:
        """Render an event per-recipient locale and send to all clients."""
        for sess in self._sessions.values():
            self._send_async(sess.writer, formatter(self._tr_for(sess.locale)))

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

    def _tr_for(
        self, locale_name: str
    ) -> gettext.NullTranslations | gettext.GNUTranslations:
        if locale_name in {"ru_RU.UTF8", "ru_RU.UTF-8"}:
            return _RU_TRANSLATION
        return gettext.NullTranslations()

    def _hp_phrase(
        self, tr: gettext.NullTranslations | gettext.GNUTranslations, value: int
    ) -> str:
        return tr.ngettext("{count} hit point", "{count} hit points", value).format(
            count=value
        )
