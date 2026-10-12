# flamegraph-studio

Small, dependency-free utilities for inspecting folded stack files used by
flame graph tooling. It parses collapsed stacks, merges duplicates, and reports
the hottest leaf frames, inclusive frames, and call-path prefixes without
inventing timing units. Recursive occurrences are counted once per sampled
stack for inclusive shares.

```text
main;parse;tokenize 17
main;parse;tokenize 3
main;render 10
```

```bash
PYTHONPATH=src python3 -m flamegraph_studio stacks.folded --top 10 --path-depth 2
PYTHONPATH=src python3 -m flamegraph_studio before.folded --compare after.folded
python3 -m unittest discover -s tests
```

Weights retain the profiler's original unit (samples, events, or time). The
tool reports proportions only after aggregating the supplied data.
Call-path prefixes group samples by their first `--path-depth` frames. A stack
shorter than that depth remains a complete path rather than being discarded.

Comparison mode ranks stack-weight changes by absolute magnitude. Because
profiler totals can differ between captures, it also ranks changes in each
stack's share of its capture. Share deltas reveal composition changes, but do
not prove that absolute execution time improved or regressed. Comparison mode
also aggregates inclusive frame shares across stack shapes, counting recursive
frames once per sampled stack. This can reveal a shifting subsystem even when
its work is split across several exact stacks. Call-path-prefix share changes
are reported at `--path-depth` as well, preserving shorter complete stacks.
They show where normalized samples moved in the call tree, not whether absolute
runtime changed.
