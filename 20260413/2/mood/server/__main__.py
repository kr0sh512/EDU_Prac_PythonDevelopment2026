"""Run the MOOD TCP server: ``python -m mood.server``.

Command-line entrypoint that binds an asyncio stream server and optionally
starts the wandering-monster background loop.
"""

from __future__ import annotations

import argparse
import asyncio

from mood.server.tcp import MudServer


async def amain(host: str, port: int, *, wandering_monsters: bool) -> None:
    """Listen on ``host``:``port`` and serve clients until cancelled.

    Args:
        host: Bind address.
        port: TCP port.
        wandering_monsters: Passed to :class:`~mood.server.tcp.MudServer`.
    """
    server = MudServer(wandering_monsters=wandering_monsters)
    asyncio.create_task(server.run_wandering_monsters())
    srv = await asyncio.start_server(server.handle_client, host=host, port=port)
    async with srv:
        await srv.serve_forever()


def main() -> None:
    """Parse CLI arguments and start the asyncio server."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4280)
    parser.add_argument(
        "--no-wander",
        action="store_true",
        help="disable periodic random monster moves (e.g. for scripted tests)",
    )
    args = parser.parse_args()
    asyncio.run(
        amain(args.host, args.port, wandering_monsters=not args.no_wander)
    )


if __name__ == "__main__":
    main()
