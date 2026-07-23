"""
sort_case.py -- interactively split a case-merged folder into two
correctly separated folders (lowercase / uppercase) on a case-sensitive volume.
"""

import argparse
import subprocess
import shutil
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--letter", required=True)
    p.add_argument("--src", required=True)
    p.add_argument("--dest", required=True)
    args = p.parse_args()

    lower = args.letter.lower()
    upper = args.letter.upper()

    src = Path(args.src)
    dest_lower = Path(args.dest) / lower
    dest_upper = Path(args.dest) / upper
    dest_lower.mkdir(parents=True, exist_ok=True)
    dest_upper.mkdir(parents=True, exist_ok=True)

    files = sorted(src.glob("*.png"))
    print(f"{len(files)} images to sort in {src}")
    print(f"For each: press l={lower!r}, u={upper!r}, s=skip, q=quit\n")

    for i, f in enumerate(files, 1):
        subprocess.Popen(["open", "-a", "Preview", str(f)])
        while True:
            choice = input(f"[{i}/{len(files)}] {f.name}  (l/u/s/q): ").strip().lower()
            if choice in ("l", "u", "s", "q"):
                break
            print("  please type l, u, s, or q")

        if choice == "q":
            print("Stopping early -- progress so far is saved.")
            break
        elif choice == "l":
            shutil.move(str(f), str(dest_lower / f.name))
        elif choice == "u":
            shutil.move(str(f), str(dest_upper / f.name))

    print(f"\nDone. {lower!r}: {len(list(dest_lower.glob('*.png')))} images, "
          f"{upper!r}: {len(list(dest_upper.glob('*.png')))} images.")


if __name__ == "__main__":
    main()
