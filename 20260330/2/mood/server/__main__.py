"""Run the MOOD TCP server: ``python -m mood.server``."""

from __future__ import annotations

import argparse
import asyncio

from mood.server.tcp import MudServer


async def amain(host: str, port: int) -> None:
    """Listen on ``host``:``port`` and serve clients forever."""
    server = MudServer()
    srv = await asyncio.start_server(server.handle_client, host=host, port=port)
    async with srv:
        await srv.serve_forever()


def main() -> None:
    """Parse CLI arguments and start the asyncio server."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4280)
    args = parser.parse_args()
    asyncio.run(amain(args.host, args.port))


if __name__ == "__main__":
    main()
