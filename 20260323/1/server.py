"""TCP MUD-сервер с несколькими именованными сессиями."""

from __future__ import annotations

import argparse
import asyncio
import shlex
from dataclasses import dataclass

from mud_engine import Dungeon, MonsterSpec


@dataclass(slots=True)
class Session:
    name: str
    writer: asyncio.StreamWriter
    pos: tuple[int, int] = (0, 0)


class MudServer:
    def __init__(self) -> None:
        self._game = Dungeon()
        self._sessions: dict[str, Session] = {}

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
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

                name = str(result["name"])
                dealt = int(result["dealt"])
                left = int(result["left"])
                if left == 0:
                    self.broadcast(
                        f"{username} attacked {name} with {weapon}: "
                        f"dealt {dealt}, {name} died"
                    )
                else:
                    self.broadcast(
                        f"{username} attacked {name} with {weapon}: "
                        f"dealt {dealt}, hp left {left}"
                    )
                return

            self.send_to(username, f"Unknown command: {cmd}")
        except (ValueError, IndexError):
            self.send_to(username, "Invalid command")

    def broadcast(self, text: str) -> None:
        for sess in self._sessions.values():
            self._send_async(sess.writer, text)

    def send_to(self, username: str, text: str) -> None:
        sess = self._sessions.get(username)
        if sess is None:
            return
        self._send_async(sess.writer, text)

    async def _send(self, writer: asyncio.StreamWriter, text: str) -> None:
        writer.write((text + "\n").encode())
        await writer.drain()

    def _send_async(self, writer: asyncio.StreamWriter, text: str) -> None:
        asyncio.create_task(self._send(writer, text))

    def _render_monster(self, name: str, hello: str) -> str:
        return f"{name} says: {hello}"


async def amain(host: str, port: int) -> None:
    server = MudServer()
    srv = await asyncio.start_server(server.handle_client, host=host, port=port)
    async with srv:
        await srv.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4280)
    args = parser.parse_args()
    asyncio.run(amain(args.host, args.port))


if __name__ == "__main__":
    main()
