from pathlib import Path
import sys

for file in Path(sys.argv[1]).glob('*.git/objects/*'):
    print(file)
