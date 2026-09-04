# flamegraph-studio

Small, dependency-free utilities for inspecting folded stack files used by
flame graph tooling. It parses collapsed stacks, merges duplicates, and reports
both the hottest leaf frames and inclusive frames without inventing timing
units. Recursive occurrences are counted once per sampled stack for inclusive
shares.

```text
main;parse;tokenize 17
main;parse;tokenize 3
main;render 10
```

```bash
PYTHONPATH=src python3 -m flamegraph_studio stacks.folded --top 10
python3 -m unittest discover -s tests
```

Weights retain the profiler's original unit (samples, events, or time). The
tool reports proportions only after aggregating the supplied data.
