"""Клиент MUD: асинхронный приём сообщений и ввод команд."""

from __future__ import annotations

import argparse
import cmd
import readline
import shlex
import socket
import threading

from mud_engine import SPECIAL_MONSTER, VERSION, WEAPONS

from cowsay import list_cows

AVAILABLE_MONSTERS = [*list_cows(), SPECIAL_MONSTER]


class InvalidCommand(RuntimeError):
    pass


def parse_addmon(parts: list[str]) -> tuple[tuple[str, str, int], int, int]:
    if not parts:
        raise InvalidCommand

    monster_name = parts[0]
    rest = parts[1:]

    values: dict[str, object] = {}
    index = 0

    while index < len(rest):
        token = rest[index]

        if token in values:
            raise InvalidCommand

        if token == "hello":
            if index + 1 >= len(rest):
                raise InvalidCommand
            values["hello"] = rest[index + 1]
            index += 2
            continue

        if token == "hp":
            if index + 1 >= len(rest):
                raise InvalidCommand
            try:
                hp_value = int(rest[index + 1])
            except ValueError:
                raise InvalidCommand
            if hp_value <= 0:
                raise InvalidCommand
            values["hp"] = hp_value
            index += 2
            continue

        if token == "coords":
            if index + 2 >= len(rest):
                raise InvalidCommand
            try:
                x_coord = int(rest[index + 1])
                y_coord = int(rest[index + 2])
            except ValueError:
                raise InvalidCommand
            values["coords"] = (x_coord, y_coord)
            index += 3
            continue

        raise InvalidCommand

    required = {"hello", "hp", "coords"}
    if set(values) != required:
        raise InvalidCommand

    x, y = values["coords"]
    hello = str(values["hello"])
    hp = int(values["hp"])
    return (monster_name, hello, hp), x, y


def parse_attack(parts: list[str]) -> tuple[str | None, str]:
    if not parts:
        return None, "sword"

    if parts[0] == "with":
        if len(parts) != 2:
            raise InvalidCommand
        return None, parts[1]

    if len(parts) == 1:
        return parts[0], "sword"

    if len(parts) == 3 and parts[1] == "with":
        return parts[0], parts[2]

    raise InvalidCommand


MOVES = {
    "right": (1, 0),
    "left": (-1, 0),
    "up": (0, 1),
    "down": (0, -1),
}


class RemoteSession:
    def __init__(self, host: str, port: int, username: str) -> None:
        self._sock = socket.create_connection((host, port))
        self._send_lock = threading.Lock()
        self._alive = True
        self._username = username
        self._buf = bytearray()
        self.send(shlex.join(["login", username]))
        reply = self.read_line()
        if reply is None or not reply.startswith("Login accepted:"):
            self._alive = False
            self._sock.close()
            if reply is None:
                raise ConnectionError("сервер закрыл соединение")
            raise ConnectionError(reply)

    def close(self) -> None:
        self._alive = False
        self._sock.close()

    @property
    def alive(self) -> bool:
        return self._alive

    def send(self, line: str) -> None:
        with self._send_lock:
            self._sock.sendall((line + "\n").encode())

    def read_line(self) -> str | None:
        while b"\n" not in self._buf:
            chunk = self._sock.recv(4096)
            if not chunk:
                return None
            self._buf.extend(chunk)
        i = self._buf.index(b"\n")
        raw = bytes(self._buf[:i]).decode(errors="replace")
        del self._buf[: i + 1]
        return raw


class GameClientRunner:
    def __init__(self, session: RemoteSession) -> None:
        self._session = session

    def process_line(self, line: str) -> None:
        try:
            parts = shlex.split(line)
            if not parts:
                return
            self.execute(parts)
        except InvalidCommand:
            print("Invalid command")
        except ConnectionError as e:
            print(e)
        except OSError as e:
            print(f"Сетевая ошибка: {e}")

    def execute(self, parts: list[str]) -> None:
        command, *args = parts

        if command in MOVES:
            if args:
                raise InvalidCommand
            dx, dy = MOVES[command]
            proto = shlex.join(["move", str(dx), str(dy)])
            self._session.send(proto)
            return

        if command == "addmon":
            (name, hello, hp), x, y = parse_addmon(args)
            proto = shlex.join(["addmon", name, hello, str(hp), str(x), str(y)])
            self._session.send(proto)
            return

        if command == "attack":
            monster_name, weapon_name = parse_attack(args)
            if weapon_name not in WEAPONS:
                print("Unknown weapon")
                return
            damage = WEAPONS[weapon_name]
            target = "*" if monster_name is None else monster_name
            proto = shlex.join(["attack", target, str(damage), weapon_name])
            self._session.send(proto)
            return

        raise InvalidCommand


class GameShell(cmd.Cmd):
    prompt = ">>> "

    def __init__(self, runner: GameClientRunner) -> None:
        super().__init__()
        self._runner = runner

    def emptyline(self) -> None:
        pass

    def default(self, line: str) -> None:
        self._runner.process_line(line)

    def do_up(self, arg: str) -> None:
        self._run("up", arg)

    def do_down(self, arg: str) -> None:
        self._run("down", arg)

    def do_left(self, arg: str) -> None:
        self._run("left", arg)

    def do_right(self, arg: str) -> None:
        self._run("right", arg)

    def do_addmon(self, arg: str) -> None:
        self._run("addmon", arg)

    def do_attack(self, arg: str) -> None:
        self._run("attack", arg)

    def complete_attack(
        self, text: str, line: str, begidx: int, endidx: int
    ) -> list[str]:
        try:
            parts = shlex.split(line[:begidx])
        except ValueError:
            return []

        if len(parts) == 1:
            return self._match([*AVAILABLE_MONSTERS, "with"], text)

        if len(parts) == 2:
            if parts[1] == "with":
                return self._match(list(WEAPONS), text)
            return self._match(["with"], text)

        if len(parts) == 3 and parts[2] == "with":
            return self._match(list(WEAPONS), text)

        return []

    def do_EOF(self, arg: str) -> bool:
        print()
        return True

    def _run(self, command: str, arg: str) -> None:
        if arg:
            self._runner.process_line(f"{command} {arg}")
        else:
            self._runner.process_line(command)

    def _match(self, options: list[str], text: str) -> list[str]:
        return [option for option in options if option.startswith(text)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("username")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4280)
    args = parser.parse_args()

    print(f"<<< Welcome to Python-MUD {VERSION} >>>")
    session = RemoteSession(args.host, args.port, args.username)

    def reader_loop() -> None:
        while session.alive:
            try:
                message = session.read_line()
                if message is None:
                    break
                line_buffer = readline.get_line_buffer()
                print("\r" + " " * 120 + "\r", end="", flush=True)
                print(message)
                print(f">>> {line_buffer}", end="", flush=True)
                readline.redisplay()
            except OSError:
                break
        session.close()

    reader = threading.Thread(target=reader_loop, daemon=True)
    reader.start()

    try:
        runner = GameClientRunner(session)
        shell = GameShell(runner)
        shell.cmdloop()
    finally:
        session.close()


if __name__ == "__main__":
    main()
