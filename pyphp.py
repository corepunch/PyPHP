import sys

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <file>", file=sys.stderr)
    sys.exit(1)

try:
    with open(sys.argv[1], 'r') as f:
        print(f.read(), end='')
except FileNotFoundError:
    print(f"{sys.argv[0]}: {sys.argv[1]}: No such file or directory", file=sys.stderr)
    sys.exit(1)
