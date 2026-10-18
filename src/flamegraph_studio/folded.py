from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class HotFrame:
    frame: str
    weight: int
    share: float


@dataclass(frozen=True)
class HotPath:
    path: tuple[str, ...]
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
class FrameShareDelta:
    frame: str
    baseline_share: float
    candidate_share: float
    share_delta: float


@dataclass(frozen=True)
class LeafShareDelta:
    frame: str
    baseline_share: float
    candidate_share: float
    share_delta: float


@dataclass(frozen=True)
class PathShareDelta:
    path: tuple[str, ...]
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
        leaves = _leaf_frame_weights(self)
        total = self.total_weight
        ranked = sorted(leaves.items(), key=lambda item: (-item[1], item[0]))
        return [HotFrame(frame, weight, weight / total) for frame, weight in ranked[:limit]]

    def hottest_frames(self, limit: int = 10) -> list[HotFrame]:
        """Rank frames by inclusive weight, counting a recursive frame once per stack."""
        if limit < 1:
            raise ValueError("limit must be positive")
        inclusive = _inclusive_frame_weights(self)
        total = self.total_weight
        ranked = sorted(inclusive.items(), key=lambda item: (-item[1], item[0]))
        return [HotFrame(frame, weight, weight / total) for frame, weight in ranked[:limit]]

    def hottest_call_paths(self, depth: int, limit: int = 10) -> list[HotPath]:
        """Rank call-path prefixes, retaining shorter stacks as complete paths."""
        if depth < 1:
            raise ValueError("depth must be positive")
        if limit < 1:
            raise ValueError("limit must be positive")
        prefixes = _call_path_weights(self, depth)
        total = self.total_weight
        ranked = sorted(prefixes.items(), key=lambda item: (-item[1], item[0]))
        return [HotPath(path, weight, weight / total) for path, weight in ranked[:limit]]


def _leaf_frame_weights(stacks: FoldedStacks) -> dict[str, int]:
    weights: dict[str, int] = {}
    for stack, weight in stacks.stacks.items():
        frame = stack[-1]
        weights[frame] = weights.get(frame, 0) + weight
    return weights


def _inclusive_frame_weights(stacks: FoldedStacks) -> dict[str, int]:
    weights: dict[str, int] = {}
    for stack, weight in stacks.stacks.items():
        for frame in set(stack):
            weights[frame] = weights.get(frame, 0) + weight
    return weights


def _call_path_weights(
    stacks: FoldedStacks, depth: int
) -> dict[tuple[str, ...], int]:
    weights: dict[tuple[str, ...], int] = {}
    for stack, weight in stacks.stacks.items():
        path = stack[:depth]
        weights[path] = weights.get(path, 0) + weight
    return weights


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
        if (
            before_weight * candidate.total_weight
            == after_weight * baseline.total_weight
        ):
            continue
        before = before_weight / baseline.total_weight
        after = after_weight / candidate.total_weight
        deltas.append(StackShareDelta(stack, before, after, after - before))
    return sorted(deltas, key=lambda item: (-abs(item.share_delta), item.stack))[:limit]


def diff_frame_shares(
    baseline: FoldedStacks, candidate: FoldedStacks, limit: int = 20
) -> list[FrameShareDelta]:
    """Rank inclusive frame-share changes across normalized captures."""
    if limit < 1:
        raise ValueError("limit must be positive")
    baseline_weights = _inclusive_frame_weights(baseline)
    candidate_weights = _inclusive_frame_weights(candidate)
    deltas: list[FrameShareDelta] = []
    for frame in baseline_weights.keys() | candidate_weights.keys():
        before_weight = baseline_weights.get(frame, 0)
        after_weight = candidate_weights.get(frame, 0)
        if (
            before_weight * candidate.total_weight
            == after_weight * baseline.total_weight
        ):
            continue
        before = before_weight / baseline.total_weight
        after = after_weight / candidate.total_weight
        deltas.append(FrameShareDelta(frame, before, after, after - before))
    return sorted(deltas, key=lambda item: (-abs(item.share_delta), item.frame))[:limit]


def diff_leaf_shares(
    baseline: FoldedStacks, candidate: FoldedStacks, limit: int = 20
) -> list[LeafShareDelta]:
    """Rank leaf-frame share changes across normalized captures."""
    if limit < 1:
        raise ValueError("limit must be positive")
    baseline_weights = _leaf_frame_weights(baseline)
    candidate_weights = _leaf_frame_weights(candidate)
    deltas: list[LeafShareDelta] = []
    for frame in baseline_weights.keys() | candidate_weights.keys():
        before_weight = baseline_weights.get(frame, 0)
        after_weight = candidate_weights.get(frame, 0)
        if (
            before_weight * candidate.total_weight
            == after_weight * baseline.total_weight
        ):
            continue
        before = before_weight / baseline.total_weight
        after = after_weight / candidate.total_weight
        deltas.append(LeafShareDelta(frame, before, after, after - before))
    return sorted(deltas, key=lambda item: (-abs(item.share_delta), item.frame))[:limit]


def diff_call_path_shares(
    baseline: FoldedStacks,
    candidate: FoldedStacks,
    depth: int,
    limit: int = 20,
) -> list[PathShareDelta]:
    """Rank normalized call-path-prefix share changes across captures."""
    if depth < 1:
        raise ValueError("depth must be positive")
    if limit < 1:
        raise ValueError("limit must be positive")
    baseline_weights = _call_path_weights(baseline, depth)
    candidate_weights = _call_path_weights(candidate, depth)
    deltas: list[PathShareDelta] = []
    for path in baseline_weights.keys() | candidate_weights.keys():
        before_weight = baseline_weights.get(path, 0)
        after_weight = candidate_weights.get(path, 0)
        if before_weight * candidate.total_weight == after_weight * baseline.total_weight:
            continue
        before = before_weight / baseline.total_weight
        after = after_weight / candidate.total_weight
        deltas.append(PathShareDelta(path, before, after, after - before))
    return sorted(deltas, key=lambda item: (-abs(item.share_delta), item.path))[:limit]
