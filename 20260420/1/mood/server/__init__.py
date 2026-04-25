"""Network server for MOOD.

Submodules:

* :mod:`mood.server.tcp` — asyncio TCP server and command handling.
* :mod:`mood.server.__main__` — ``python -m mood.server`` CLI entrypoint.
"""

from mood.server.__main__ import run_server

__all__ = ["run_server"]
