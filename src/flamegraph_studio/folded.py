from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class HotFrame:
    frame: str
    weight: int
    share: float


@dataclass(frozen=True)
class FoldedStacks:
    stacks: dict[tuple[str, ...], int]

    @property
    def total_weight(self) -> int:
        return sum(self.stacks.values())

    def hottest_leaves(self, limit: int = 10) -> list[HotFrame]:
        if limit < 1:
            raise ValueError("limit must be positive")
        leaves: dict[str, int] = {}
        for stack, weight in self.stacks.items():
            leaves[stack[-1]] = leaves.get(stack[-1], 0) + weight
        total = self.total_weight
        ranked = sorted(leaves.items(), key=lambda item: (-item[1], item[0]))
        return [HotFrame(frame, weight, weight / total) for frame, weight in ranked[:limit]]

    def hottest_frames(self, limit: int = 10) -> list[HotFrame]:
        """Rank frames by inclusive weight, counting a recursive frame once per stack."""
        if limit < 1:
            raise ValueError("limit must be positive")
        inclusive: dict[str, int] = {}
        for stack, weight in self.stacks.items():
            for frame in set(stack):
                inclusive[frame] = inclusive.get(frame, 0) + weight
        total = self.total_weight
        ranked = sorted(inclusive.items(), key=lambda item: (-item[1], item[0]))
        return [HotFrame(frame, weight, weight / total) for frame, weight in ranked[:limit]]


def parse_folded(lines: Iterable[str]) -> FoldedStacks:
    stacks: dict[tuple[str, ...], int] = {}
    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            stack_text, weight_text = line.rsplit(maxsplit=1)
            stack = tuple(stack_text.split(";"))
            weight = int(weight_text)
        except (ValueError, TypeError) as error:
            raise ValueError(f"invalid folded stack on line {line_number}") from error
        if any(not frame for frame in stack) or weight <= 0:
            raise ValueError(f"invalid folded stack on line {line_number}")
        stacks[stack] = stacks.get(stack, 0) + weight
    if not stacks:
        raise ValueError("at least one folded stack is required")
    return FoldedStacks(stacks)
