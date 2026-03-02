import shlex

while True:
    try:
        line = input('==> ')
        if not line:
            continue
        parts = shlex.split(line)
        params = parts[1:]
        print(parts[0], len(params), params)
        print(shlex.join(parts[1:]))
    except (EOFError, KeyboardInterrupt):
        break

