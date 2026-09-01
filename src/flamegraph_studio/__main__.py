import argparse
from dataclasses import asdict
import json
from pathlib import Path

from .folded import parse_folded


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect folded stack data")
    parser.add_argument("path", type=Path)
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()
    with args.path.open(encoding="utf-8") as source:
        stacks = parse_folded(source)
    payload = {
        "stack_count": len(stacks.stacks),
        "total_weight": stacks.total_weight,
        "hottest_leaves": [asdict(item) for item in stacks.hottest_leaves(args.top)],
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

