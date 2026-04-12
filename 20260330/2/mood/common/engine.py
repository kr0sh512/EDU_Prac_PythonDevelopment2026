"""Pure game state and rules without networking or cowsay rendering."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "VERSION",
    "SPECIAL_MONSTER",
    "WEAPONS",
    "MonsterSpec",
    "CellEvent",
    "Monster",
    "Dungeon",
]

VERSION = 0.1
SPECIAL_MONSTER = "jgsbat"
WEAPONS = {
    "sword": 10,
    "spear": 15,
    "axe": 20,
}


@dataclass(slots=True)
class MonsterSpec:
    """Static data describing a monster placed on the dungeon grid."""

    name: str
    hello: str
    hp: int


class CellEvent:
    """Base cell content; empty cells are falsy."""

    def __init__(self, empty: bool = True) -> None:
        """Create a cell, empty by default."""
        self._empty = empty

    def __bool__(self) -> bool:
        """Return whether the cell holds something."""
        return not self._empty


class Monster(CellEvent):
    """A monster instance with mutable hit points."""

    def __init__(self, spec: MonsterSpec) -> None:
        """Wrap ``spec`` as live cell content."""
        super().__init__(empty=False)
        self._spec = spec

    @property
    def name(self) -> str:
        """Return the monster name."""
        return self._spec.name

    @property
    def hello(self) -> str:
        """Return the monster greeting string."""
        return self._spec.hello

    @property
    def hp(self) -> int:
        """Return current hit points."""
        return self._spec.hp

    @hp.setter
    def hp(self, value: int) -> None:
        """Set hit points to ``value``."""
        self._spec.hp = value


class Dungeon:
    """Toroidal grid with movement and combat rules."""

    def __init__(self, side: int = 10) -> None:
        """Build a ``side`` by ``side`` dungeon and clear it."""
        self._side = side
        self._field: list[list[CellEvent]] = []
        self.clear()

    @property
    def side(self) -> int:
        """Return grid width and height."""
        return self._side

    def clear(self) -> None:
        """Reset every cell to empty."""
        self._field = [
            [CellEvent() for _ in range(self._side)] for _ in range(self._side)
        ]

    def _shift(self, pos: tuple[int, int], dx: int, dy: int) -> tuple[int, int]:
        x, y = pos
        return ((x + dx) % self._side, (y + dy) % self._side)

    def _unpack_coords(self, key: tuple[int, int]) -> tuple[int, int]:
        if not isinstance(key, tuple) or len(key) != 2:
            raise KeyError
        return key

    def __getitem__(self, key: tuple[int, int]) -> CellEvent:
        """Return the cell at integer coordinates ``key``."""
        x, y = self._unpack_coords(key)
        return self._field[x][y]

    def __setitem__(self, key: tuple[int, int], value: CellEvent) -> None:
        """Assign ``value`` to the cell at ``key``."""
        x, y = self._unpack_coords(key)
        self._field[x][y] = value

    def move(
        self, pos: tuple[int, int], dx: int, dy: int
    ) -> tuple[tuple[int, int], dict[str, str] | None]:
        """Move from ``pos`` by ``dx``, ``dy`` and report any encounter."""
        pos = self._shift(pos, dx, dy)
        current = self[pos]
        if isinstance(current, Monster):
            return pos, {"name": current.name, "hello": current.hello}
        return pos, None

    def place_monster(self, x: int, y: int, spec: MonsterSpec) -> bool:
        """Place a monster from ``spec`` at ``(x, y)``; return whether replaced."""
        replaced = bool(self[x, y])
        self[x, y] = Monster(MonsterSpec(spec.name, spec.hello, spec.hp))
        return replaced

    def attack(
        self, pos: tuple[int, int], monster_name: str | None, damage: int
    ) -> dict[str, object]:
        """Apply ``damage`` to a monster at ``pos``; validate ``monster_name``."""
        current = self[pos]

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
            self[pos] = CellEvent()
        return {"ok": True, "name": name, "dealt": dealt, "left": left}
