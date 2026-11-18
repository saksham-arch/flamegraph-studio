from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from flamegraph_studio.__main__ import main

from flamegraph_studio import (
    diff_call_path_shares,
    diff_depth_shares,
    diff_folded,
    diff_frame_shares,
    diff_leaf_shares,
    diff_stack_shares,
    parse_folded,
)


class FoldedStackTests(unittest.TestCase):
    def test_compares_depth_shares_with_unequal_capture_totals(self) -> None:
        baseline = parse_folded(["root;work 3", "root;deep;work 1"])
        candidate = parse_folded(["root;work 2", "root;deep;work 6"])

        changes = diff_depth_shares(baseline, candidate)

        self.assertEqual([item.depth for item in changes], [2, 3])
        self.assertAlmostEqual(changes[0].share_delta, -0.5)
        self.assertAlmostEqual(changes[1].share_delta, 0.5)

    def test_compare_output_reports_stack_depth_change(self) -> None:
        with TemporaryDirectory() as directory:
            baseline = Path(directory) / "baseline.folded"
            candidate = Path(directory) / "candidate.folded"
            baseline.write_text("main;work 2\n", encoding="utf-8")
            candidate.write_text("main;parse;work 2\n", encoding="utf-8")
            output = StringIO()
            with patch("sys.argv", ["flamegraph-studio", str(baseline), "--compare", str(candidate)]):
                with redirect_stdout(output):
                    main()
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["baseline_stack_depth"]["weighted_mean_depth"], 2)
        self.assertEqual(payload["candidate_stack_depth"]["weighted_mean_depth"], 3)
        self.assertEqual(payload["weighted_mean_depth_change"], 1)

    def test_merges_duplicates_and_ranks_leaves(self) -> None:
        result = parse_folded(
            ["main;parse;tokenize 17\n", "main;parse;tokenize 3\n", "main;render 10\n"]
        )
        self.assertEqual(len(result.stacks), 2)
        self.assertEqual(result.total_weight, 30)
        hottest = result.hottest_leaves()
        self.assertEqual((hottest[0].frame, hottest[0].weight), ("tokenize", 20))
        self.assertAlmostEqual(hottest[0].share, 2 / 3)

    def test_summarizes_stack_depth_by_sample_weight(self) -> None:
        result = parse_folded(
            ["main;parse;tokenize 20", "main;render 10", "cleanup 2"]
        )

        summary = result.depth_summary()

        self.assertEqual(summary.minimum_depth, 1)
        self.assertEqual(summary.weighted_median_depth, 3)
        self.assertEqual(summary.weighted_mean_depth, 82 / 32)
        self.assertEqual(summary.maximum_depth, 3)

    def test_depth_histogram_merges_shapes_and_uses_sample_weight(self) -> None:
        result = parse_folded(
            [
                "main;parse;tokenize 17",
                "main;parse;validate 3",
                "main;render 10",
                "cleanup 2",
            ]
        )

        buckets = result.depth_histogram()

        self.assertEqual(
            [(item.depth, item.weight) for item in buckets],
            [(1, 2), (2, 10), (3, 20)],
        )
        self.assertAlmostEqual(sum(item.share for item in buckets), 1.0)
        self.assertAlmostEqual(buckets[-1].share, 20 / 32)

    def test_single_capture_output_includes_depth_histogram(self) -> None:
        with TemporaryDirectory() as directory:
            capture = Path(directory) / "capture.folded"
            capture.write_text("main;work 3\nmain;other 1\ncleanup 1\n", encoding="utf-8")
            output = StringIO()
            with patch("sys.argv", ["flamegraph-studio", str(capture)]):
                with redirect_stdout(output):
                    main()
        payload = json.loads(output.getvalue())
        self.assertEqual(
            payload["stack_depth_histogram"],
            [
                {"depth": 1, "weight": 1, "share": 0.2},
                {"depth": 2, "weight": 4, "share": 0.8},
            ],
        )

    def test_rejects_empty_or_invalid_input(self) -> None:
        for lines in ([], ["main;work 0"], ["not-folded"]):
            with self.subTest(lines=lines), self.assertRaises(ValueError):
                parse_folded(lines)

    def test_validates_limit(self) -> None:
        with self.assertRaises(ValueError):
            parse_folded(["main 1"]).hottest_leaves(0)

    def test_ranks_inclusive_frames_without_double_counting_recursion(self) -> None:
        result = parse_folded(["main;parse;parse 20", "main;render 10"])
        frames = result.hottest_frames()
        self.assertEqual((frames[0].frame, frames[0].weight, frames[0].share), ("main", 30, 1.0))
        self.assertEqual((frames[1].frame, frames[1].weight), ("parse", 20))

    def test_validates_inclusive_limit(self) -> None:
        with self.assertRaises(ValueError):
            parse_folded(["main 1"]).hottest_frames(0)

    def test_aggregates_hot_call_path_prefixes(self) -> None:
        result = parse_folded(
            [
                "main;parse;tokenize 17",
                "main;parse;validate 3",
                "main;render;paint 10",
                "cleanup 2",
            ]
        )

        paths = result.hottest_call_paths(depth=2)

        self.assertEqual(
            [(item.path, item.weight) for item in paths],
            [(("main", "parse"), 20), (("main", "render"), 10), (("cleanup",), 2)],
        )
        self.assertAlmostEqual(paths[0].share, 20 / 32)

    def test_validates_call_path_options(self) -> None:
        result = parse_folded(["main 1"])
        with self.assertRaises(ValueError):
            result.hottest_call_paths(0)
        with self.assertRaises(ValueError):
            result.hottest_call_paths(1, limit=0)

    def test_diffs_folded_stack_weights(self) -> None:
        baseline = parse_folded(["main;parse 10", "main;render 5"])
        candidate = parse_folded(["main;parse 14", "main;write 8"])
        deltas = diff_folded(baseline, candidate)
        self.assertEqual(
            [(item.stack, item.weight_delta) for item in deltas],
            [(('main', 'write'), 8), (('main', 'render'), -5), (('main', 'parse'), 4)],
        )

    def test_validates_diff_limit(self) -> None:
        stacks = parse_folded(["main 1"])
        with self.assertRaises(ValueError):
            diff_folded(stacks, stacks, 0)

    def test_diffs_normalized_stack_shares_across_unequal_captures(self) -> None:
        baseline = parse_folded(["main;parse 60", "main;render 40"])
        candidate = parse_folded(
            ["main;parse 90", "main;render 10", "main;write 100"]
        )

        deltas = diff_stack_shares(baseline, candidate)

        self.assertEqual([item.stack for item in deltas], [
            ("main", "write"),
            ("main", "render"),
            ("main", "parse"),
        ])
        self.assertAlmostEqual(deltas[0].share_delta, 0.5)
        self.assertAlmostEqual(deltas[1].share_delta, -0.35)
        self.assertAlmostEqual(deltas[2].share_delta, -0.15)

    def test_omits_unchanged_shares_when_capture_sizes_differ(self) -> None:
        baseline = parse_folded(["main;parse 3", "main;render 1"])
        candidate = parse_folded(["main;parse 6", "main;render 2"])
        self.assertEqual(diff_stack_shares(baseline, candidate), [])

    def test_validates_share_diff_limit(self) -> None:
        stacks = parse_folded(["main 1"])
        with self.assertRaises(ValueError):
            diff_stack_shares(stacks, stacks, 0)

    def test_diffs_inclusive_frame_shares_across_stack_shapes(self) -> None:
        baseline = parse_folded(
            ["main;parse;tokenize 60", "main;render 40"]
        )
        candidate = parse_folded(
            [
                "main;parse;validate 20",
                "main;render 80",
                "worker;parse;tokenize 100",
            ]
        )

        deltas = diff_frame_shares(baseline, candidate)
        by_frame = {item.frame: item for item in deltas}

        self.assertNotIn("parse", by_frame)
        self.assertAlmostEqual(by_frame["main"].share_delta, -0.5)
        self.assertAlmostEqual(by_frame["worker"].share_delta, 0.5)
        self.assertAlmostEqual(by_frame["tokenize"].share_delta, -0.1)

    def test_frame_share_diff_counts_recursion_once_per_stack(self) -> None:
        baseline = parse_folded(["main;parse;parse 10"])
        candidate = parse_folded(["main;parse 20"])
        self.assertEqual(diff_frame_shares(baseline, candidate), [])

    def test_validates_frame_share_diff_limit(self) -> None:
        stacks = parse_folded(["main 1"])
        with self.assertRaises(ValueError):
            diff_frame_shares(stacks, stacks, 0)

    def test_diffs_leaf_shares_without_counting_callers(self) -> None:
        baseline = parse_folded(["main;parse 60", "main;render 40"])
        candidate = parse_folded(["main;parse 20", "main;render 80"])

        deltas = diff_leaf_shares(baseline, candidate)
        by_frame = {item.frame: item for item in deltas}

        self.assertAlmostEqual(by_frame["parse"].share_delta, -0.4)
        self.assertAlmostEqual(by_frame["render"].share_delta, 0.4)
        self.assertNotIn("main", by_frame)

    def test_validates_leaf_share_diff_limit(self) -> None:
        stacks = parse_folded(["main 1"])
        with self.assertRaises(ValueError):
            diff_leaf_shares(stacks, stacks, 0)

    def test_diffs_normalized_call_path_prefix_shares(self) -> None:
        baseline = parse_folded(
            ["main;parse;tokenize 60", "main;render 40"]
        )
        candidate = parse_folded(
            ["main;parse;validate 20", "main;render 80", "worker;sync 100"]
        )

        deltas = diff_call_path_shares(baseline, candidate, depth=2)
        by_path = {item.path: item for item in deltas}

        self.assertAlmostEqual(by_path[("worker", "sync")].share_delta, 0.5)
        self.assertAlmostEqual(by_path[("main", "parse")].share_delta, -0.5)
        self.assertNotIn(("main", "render"), by_path)

    def test_validates_call_path_share_diff_options(self) -> None:
        stacks = parse_folded(["main 1"])
        with self.assertRaises(ValueError):
            diff_call_path_shares(stacks, stacks, depth=0)
        with self.assertRaises(ValueError):
            diff_call_path_shares(stacks, stacks, depth=1, limit=0)


if __name__ == "__main__":
    unittest.main()
