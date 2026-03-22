"""Игровое состояние и правила MUD без ввода-вывода и без cowsay."""

from __future__ import annotations

from dataclasses import dataclass

VERSION = 0.1
SPECIAL_MONSTER = "jgsbat"
WEAPONS = {
    "sword": 10,
    "spear": 15,
    "axe": 20,
}


@dataclass(slots=True)
class MonsterSpec:
    name: str
    hello: str
    hp: int


class CellEvent:
    def __init__(self, empty: bool = True):
        self._empty = empty

    def __bool__(self) -> bool:
        return not self._empty


class Monster(CellEvent):
    def __init__(self, spec: MonsterSpec):
        super().__init__(empty=False)
        self._spec = spec

    @property
    def name(self) -> str:
        return self._spec.name

    @property
    def hello(self) -> str:
        return self._spec.hello

    @property
    def hp(self) -> int:
        return self._spec.hp

    @hp.setter
    def hp(self, value: int) -> None:
        self._spec.hp = value


class Dungeon:
    def __init__(self, side: int = 10):
        self._side = side
        self._field: list[list[CellEvent]] = []
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

    def _shift(self, dx: int, dy: int) -> tuple[int, int]:
        x, y = self._player
        self._player = ((x + dx) % self._side, (y + dy) % self._side)
        return self._player

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

    def move(self, dx: int, dy: int) -> tuple[tuple[int, int], dict[str, str] | None]:
        pos = self._shift(dx, dy)
        current = self[pos]
        if isinstance(current, Monster):
            return pos, {"name": current.name, "hello": current.hello}
        return pos, None

    def place_monster(self, x: int, y: int, spec: MonsterSpec) -> bool:
        replaced = bool(self[x, y])
        self[x, y] = Monster(MonsterSpec(spec.name, spec.hello, spec.hp))
        return replaced

    def attack(
        self, monster_name: str | None, damage: int
    ) -> dict[str, object]:
        current = self[self._player]

        if monster_name is None:
            if not isinstance(current, Monster):
                return {"ok": False, "why": "empty"}
        else:
            if not isinstance(current, Monster) or current.name != monster_name:
                return {"ok": False, "why": "wrong_name", "name": monster_name}

        assert isinstance(current, Monster)
        dealt = min(damage, current.hp)
        current.hp -= dealt
        left = current.hp
        name = current.name
        if left == 0:
            self[self._player] = CellEvent()
        return {"ok": True, "name": name, "dealt": dealt, "left": left}
