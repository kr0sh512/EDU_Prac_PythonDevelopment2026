import cmd
import shlex

from dataclasses import dataclass
from cowsay import cowsay, list_cows, read_dot_cow


VERSION = 0.1
SPECIAL_MONSTER = "jgsbat"
AVAILABLE_MONSTERS = [*list_cows(), SPECIAL_MONSTER]
WEAPONS = {
    "sword": 10,
    "spear": 15,
    "axe": 20,
}

with open("jgsbat") as f:
    JGSBAT_COW = read_dot_cow(f)


class InvalidCommand(RuntimeError):
    pass


class UnknownMonster(RuntimeError):
    pass


class CellEvent:
    def __init__(self, empty: bool = True):
        self._empty = empty

    def __bool__(self) -> bool:
        return not self._empty


@dataclass(slots=True)
class MonsterSpec:
    name: str
    hello: str
    hp: int


class Monster(CellEvent):
    def __init__(self, spec: MonsterSpec):
        super().__init__(empty=False)
        self._spec = spec

    @property
    def name(self) -> str:
        return self._spec.name

    @property
    def hp(self) -> int:
        return self._spec.hp

    @hp.setter
    def hp(self, value: int) -> None:
        self._spec.hp = value

    def speak(self) -> str:
        if self._spec.name == SPECIAL_MONSTER:
            return cowsay(message=self._spec.hello, cowfile=JGSBAT_COW)
        return cowsay(message=self._spec.hello, cow=self._spec.name)


class Dungeon:
    def __init__(self, side: int = 10):
        self._side = side
        self._field = []
        self._player = (0, 0)
        self.clear()

    @property
    def side(self) -> int:
        return self._side

    @property
    def position(self) -> tuple[int, int]:
        return self._player

    def clear(self) -> None:
        self._field = [
            [CellEvent() for _ in range(self._side)] for _ in range(self._side)
        ]

    def start(self) -> None:
        print(f"<<< Welcome to Python-MUD {VERSION} >>>")
        self._player = (0, 0)

    def _shift(self, dx: int, dy: int) -> tuple[int, int]:
        x, y = self._player
        self._player = ((x + dx) % self._side, (y + dy) % self._side)
        return self._player

    def right(self) -> tuple[int, int]:
        return self._shift(1, 0)

    def left(self) -> tuple[int, int]:
        return self._shift(-1, 0)

    def up(self) -> tuple[int, int]:
        return self._shift(0, 1)

    def down(self) -> tuple[int, int]:
        return self._shift(0, -1)

    def _unpack_coords(self, key: tuple[int, int]) -> tuple[int, int]:
        if not isinstance(key, tuple) or len(key) != 2:
            raise KeyError
        return key

    def __getitem__(self, key: tuple[int, int]) -> CellEvent:
        x, y = self._unpack_coords(key)
        return self._field[x][y]

    def __setitem__(self, key: tuple[int, int], value: CellEvent) -> None:
        x, y = self._unpack_coords(key)
        self._field[x][y] = value

    def place_monster(self, x: int, y: int, spec: MonsterSpec) -> CellEvent:
        if spec.name not in AVAILABLE_MONSTERS:
            raise UnknownMonster
        self[x, y] = Monster(MonsterSpec(spec.name, spec.hello, spec.hp))
        return self[x, y]

    def trigger_cell(self, x: int, y: int) -> list[str]:
        current = self[x, y]
        if isinstance(current, Monster):
            return [current.speak()]
        return []

    def attack(self, monster_name: str | None, damage: int) -> list[str]:
        current = self[self._player]

        if monster_name is None:
            if not isinstance(current, Monster):
                return ["No monster here"]
        else:
            if not isinstance(current, Monster) or current.name != monster_name:
                return [f"No {monster_name} here"]

        dealt = min(damage, current.hp)
        current.hp -= dealt

        messages = [f"Attacked {current.name}, damage {dealt} hp"]

        if current.hp == 0:
            messages.append(f"{current.name} died")
            self[self._player] = CellEvent()
        else:
            messages.append(f"{current.name} now has {current.hp}")

        return messages


def parse_addmon(parts: list[str]) -> tuple[MonsterSpec, int, int]:
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
    spec = MonsterSpec(
        name=monster_name,
        hello=values["hello"],
        hp=values["hp"],
    )
    return spec, x, y


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


class GameRunner:
    def __init__(self, game: Dungeon):
        self._game = game
        self._moves = {
            "right": self._game.right,
            "left": self._game.left,
            "up": self._game.up,
            "down": self._game.down,
        }

    def process_line(self, line: str) -> None:
        try:
            parts = shlex.split(line)
            if not parts:
                return

            for message in self.execute(parts):
                print(message)
        except UnknownMonster:
            print("Cannot add unknown monster")
        except Exception:
            print("Invalid command")

    def execute(self, parts: list[str]) -> list[str]:
        command, *args = parts

        if command in self._moves:
            if args:
                raise InvalidCommand
            x, y = self._moves[command]()
            return [f"Moved to ({x}, {y})", *self._game.trigger_cell(x, y)]

        if command == "addmon":
            spec, x, y = parse_addmon(args)
            replaced = bool(self._game[x, y])
            self._game.place_monster(x, y, spec)

            messages = [f"Added monster to ({x}, {y}) saying {spec.hello}"]
            if replaced:
                messages.append("Replaced the old monster")
            return messages

        if command == "attack":
            monster_name, weapon_name = parse_attack(args)
            if weapon_name not in WEAPONS:
                return ["Unknown weapon"]
            return self._game.attack(monster_name, WEAPONS[weapon_name])

        raise InvalidCommand


class GameShell(cmd.Cmd):
    prompt = ">>> "

    def __init__(self, runner: GameRunner):
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
    game = Dungeon()
    game.start()

    runner = GameRunner(game)
    shell = GameShell(runner)
    shell.cmdloop()


if __name__ == "__main__":
    main()
