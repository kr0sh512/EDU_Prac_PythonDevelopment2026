import sys
from cowsay import cowsay


class Event:
    def __init__(self, nothing: bool = True):
        self._nothing = nothing

        return

    def __bool__(self):
        return not self._nothing


class Monster(Event):
    def __init__(self, message: str | None = None):
        super().__init__(nothing=False)
        self._message = message

        return

    def say(self):
        if self._message:
            print(cowsay(message=self._message))

        return


class DungeonGame:
    def __init__(self, size: int = 10):
        self.size = size
        self.reset()

        return

    @property
    def x(self) -> int:
        return self.pos[0]

    @property
    def y(self) -> int:
        return self.pos[1]

    def reset(self) -> None:
        self._dungeon = [[Event() for _ in range(self.size)] for _ in range(self.size)]

        return

    def start(self):
        self.pos: tuple[int, int] = (0, 0)

    def move(self, dx: int = 0, dy: int = 0) -> tuple[int, int]:
        x, y = self.pos
        self.pos = ((x + dx) % self.size, (y + dy) % self.size)

        return self.pos

    def addmon(self, pos: tuple[int, int], message: str) -> Event:
        x, y = pos
        self[x, y] = Monster(message)

        return self[x, y]

    def encounter(self, x: int, y: int) -> None:
        event = self[x, y]

        if isinstance(event, Monster):
            event.say()

        return

    def __getitem__(self, key: tuple[int, int]) -> Event:
        if isinstance(key, tuple) and len(key) == 2:
            x, y = key

            return self._dungeon[x][y]

        raise KeyError

    def __setitem__(self, key: tuple[int, int], event: Event):
        if isinstance(key, tuple) and len(key) == 2:
            x, y = key
            self._dungeon[x][y] = event

            return

        raise KeyError


def main():
    game = DungeonGame()
    game.start()

    for line in sys.stdin:
        command, *args = line.split()
        try:
            if command in ["right", "left", "up", "down"] and len(args) == 0:
                if command == "up":
                    game.move(dy=1)
                if command == "down":
                    game.move(dy=-1)
                if command == "right":
                    game.move(dx=1)
                if command == "left":
                    game.move(dx=-1)

                x, y = game.pos
                print(f"Moved to ({x}, {y})")
                game.encounter(x, y)

            elif command == "addmon" and len(args) == 3:
                x, y, message = args
                x = int(x)
                y = int(y)

                is_replace = bool(game[x, y])

                game.addmon((x, y), message=message)
                print(f"Added monster to ({x}, {y}) saying {message}")

                if is_replace:
                    print("Replaced the old monster")
            else:
                raise RuntimeError("Invalid command")

        except Exception as e:
            print(e)

    return


if __name__ == "__main__":
    main()
