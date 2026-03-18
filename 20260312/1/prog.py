import sys
import shlex

from dataclasses import dataclass
from cowsay import cowsay, list_cows, read_dot_cow


VERSION = 0.1
SPECIAL_MONSTER = "jgsbat"
AVAILABLE_MONSTERS = [*list_cows(), SPECIAL_MONSTER]

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


@dataclass(frozen=True, slots=True)
class MonsterSpec:
    name: str
    hello: str
    hp: int


class Monster(CellEvent):
    def __init__(self, spec: MonsterSpec):
        super().__init__(empty=False)
        self._spec = spec

    def speak(self) -> None:
        if self._spec.name == SPECIAL_MONSTER:
            print(cowsay(message=self._spec.hello, cowfile=JGSBAT_COW))
            return
        print(cowsay(message=self._spec.hello, cow=self._spec.name))


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

    def trigger_cell(self, x: int, y: int) -> None:
        current = self[x, y]
        if isinstance(current, Monster):
            current.speak()


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


def main() -> None:
    game = Dungeon()
    game.start()

    moves = {
        "right": game.right,
        "left": game.left,
        "up": game.up,
        "down": game.down,
    }

    for raw_line in sys.stdin:
        try:
            parts = shlex.split(raw_line)
            if not parts:
                raise InvalidCommand

            cmd, *args = parts

            if cmd in moves:
                if args:
                    raise InvalidCommand
                x, y = moves[cmd]()
                print(f"Moved to ({x}, {y})")
                game.trigger_cell(x, y)
                continue

            if cmd == "addmon":
                spec, x, y = parse_addmon(args)
                replaced = bool(game[x, y])

                game.place_monster(x, y, spec)
                print(f"Added monster to ({x}, {y}) saying {spec.hello}")
                if replaced:
                    print("Replaced the old monster")
                continue

            raise InvalidCommand

        except UnknownMonster:
            print("Cannot add unknown monster")
        except Exception:
            print("Invalid command")


if __name__ == "__main__":
    main()
