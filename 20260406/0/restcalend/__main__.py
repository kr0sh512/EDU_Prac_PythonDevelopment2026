"""Very useful doc"""

from calendar import month
import argparse


def f():
    """Not so useful doc"""
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("year", type=int, help="Year")
    parser.add_argument("month", type=int, help="Month")
    args = parser.parse_args()

    # print(month(args.year, args.month))

    cal = month(args.year, args.month).splitlines()
    # cal = [line.strip() for line in cal]

    print("cal")
    print("===")
    print(f".. table:: {cal[0].strip()}")
    print()
    print("    == == == == == == ==")
    print(f"    {cal[1]}")
    print("    == == == == == == ==")
    print(f"    {cal[2].replace("   ", "\\  ")}")
    print(*[f"    {i}\n" for i in cal[3:]], sep="", end="")
    print("    == == == == == == ==")
