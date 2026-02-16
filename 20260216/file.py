from pathlib import Path
import sys
import zlib

data = zlib.decompress(Path(sys.argv[1]).read_bytes())
print(data)

