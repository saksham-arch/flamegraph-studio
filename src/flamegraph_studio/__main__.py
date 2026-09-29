import argparse
from dataclasses import asdict
import json
from pathlib import Path

from .folded import diff_folded, diff_stack_shares, parse_folded


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect folded stack data")
    parser.add_argument("path", type=Path)
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument(
        "--path-depth", type=int, default=2, help="depth for hot call-path prefixes"
    )
    parser.add_argument("--compare", type=Path, help="candidate folded stacks")
    args = parser.parse_args()
    with args.path.open(encoding="utf-8") as source:
        stacks = parse_folded(source)
    if args.compare is not None:
        with args.compare.open(encoding="utf-8") as source:
            candidate = parse_folded(source)
        payload = {
            "baseline_total_weight": stacks.total_weight,
            "candidate_total_weight": candidate.total_weight,
            "largest_stack_changes": [
                asdict(item) for item in diff_folded(stacks, candidate, args.top)
            ],
            "largest_stack_share_changes": [
                asdict(item)
                for item in diff_stack_shares(stacks, candidate, args.top)
            ],
        }
    else:
        payload = {
            "stack_count": len(stacks.stacks),
            "total_weight": stacks.total_weight,
            "hottest_leaves": [asdict(item) for item in stacks.hottest_leaves(args.top)],
            "hottest_frames": [asdict(item) for item in stacks.hottest_frames(args.top)],
            "hottest_call_paths": [
                asdict(item)
                for item in stacks.hottest_call_paths(args.path_depth, args.top)
            ],
        }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
