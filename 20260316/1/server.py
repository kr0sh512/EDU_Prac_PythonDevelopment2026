"""TCP-сервер MUD: одна строка запроса → одна строка JSON-ответа."""

from __future__ import annotations

import argparse
import json
import shlex
import socket
from typing import Any

from mud_engine import Dungeon, MonsterSpec


def _handle(game: Dungeon, parts: list[str]) -> dict[str, Any]:
    cmd = parts[0]
    if cmd == "move":
        dx, dy = int(parts[1]), int(parts[2])
        (x, y), encounter = game.move(dx, dy)
        return {"t": "move", "x": x, "y": y, "encounter": encounter}

    if cmd == "addmon":
        _, name, hello, hp_s, xs, ys = parts
        hp, x, y = int(hp_s), int(xs), int(ys)
        replaced = game.place_monster(x, y, MonsterSpec(name, hello, hp))
        return {
            "t": "addmon",
            "x": x,
            "y": y,
            "hello": hello,
            "replaced": replaced,
        }

    if cmd == "attack":
        target, dmg_s = parts[1], parts[2]
        damage = int(dmg_s)
        monster_name: str | None = None if target == "*" else target
        result = game.attack(monster_name, damage)
        return {"t": "attack", **result}

    return {"t": "proto_error", "msg": f"unknown command {cmd!r}"}


def _session(conn: socket.socket, game: Dungeon) -> None:
    buf = bytearray()
    while True:
        while b"\n" not in buf:
            chunk = conn.recv(4096)
            if not chunk:
                return
            buf.extend(chunk)
        i = buf.index(b"\n")
        raw = bytes(buf[:i]).decode()
        del buf[: i + 1]
        line = raw.strip()
        if not line:
            continue
        parts = shlex.split(line)
        try:
            payload = _handle(game, parts)
        except (ValueError, IndexError) as e:
            payload = {"t": "proto_error", "msg": str(e)}
        conn.sendall((json.dumps(payload, ensure_ascii=False) + "\n").encode())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4280)
    args = parser.parse_args()

    game = Dungeon()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((args.host, args.port))
        sock.listen(1)
        while True:
            conn, _ = sock.accept()
            with conn:
                _session(conn, game)


if __name__ == "__main__":
    main()
