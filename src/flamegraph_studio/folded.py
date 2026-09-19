from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class HotFrame:
    frame: str
    weight: int
    share: float


@dataclass(frozen=True)
class StackDelta:
    stack: tuple[str, ...]
    baseline_weight: int
    candidate_weight: int
    weight_delta: int


@dataclass(frozen=True)
class StackShareDelta:
    stack: tuple[str, ...]
    baseline_share: float
    candidate_share: float
    share_delta: float


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


def diff_folded(
    baseline: FoldedStacks, candidate: FoldedStacks, limit: int = 20
) -> list[StackDelta]:
    if limit < 1:
        raise ValueError("limit must be positive")
    deltas: list[StackDelta] = []
    for stack in baseline.stacks.keys() | candidate.stacks.keys():
        before = baseline.stacks.get(stack, 0)
        after = candidate.stacks.get(stack, 0)
        if before != after:
            deltas.append(StackDelta(stack, before, after, after - before))
    return sorted(deltas, key=lambda item: (-abs(item.weight_delta), item.stack))[:limit]


def diff_stack_shares(
    baseline: FoldedStacks, candidate: FoldedStacks, limit: int = 20
) -> list[StackShareDelta]:
    """Rank stack share changes after normalizing each capture by its total."""
    if limit < 1:
        raise ValueError("limit must be positive")
    deltas: list[StackShareDelta] = []
    for stack in baseline.stacks.keys() | candidate.stacks.keys():
        before_weight = baseline.stacks.get(stack, 0)
        after_weight = candidate.stacks.get(stack, 0)
        if before_weight * candidate.total_weight == after_weight * baseline.total_weight:
            continue
        before = before_weight / baseline.total_weight
        after = after_weight / candidate.total_weight
        deltas.append(StackShareDelta(stack, before, after, after - before))
    return sorted(deltas, key=lambda item: (-abs(item.share_delta), item.stack))[:limit]
