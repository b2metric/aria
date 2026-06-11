# codegraph/ — code knowledge graph (engineering-core:code-knowledge-graph)

Dev-time code/architecture graph + drift audit (NOT runtime agent memory).

```bash
python codegraph/build_graph.py --backend backend/app --frontend frontend/src \
  --decisions LOCKED-DECISIONS.md --out codegraph          # generate
python codegraph/build_graph.py --check                    # CI drift gate (exit 1 on drift)
python codegraph/build_graph.py --enrich                   # + LLM community summaries (role-architect)
```

Outputs (git-ignored, regenerated): `graph.json`, `graph.html`, `drift-audit.json`.
architecture-guardian reads `drift-audit.json` before approving structural changes.
