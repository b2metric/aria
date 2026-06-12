#!/usr/bin/env python3
"""engineering-core:code-knowledge-graph — hybrid code/architecture graph generator.

Static backbone (stdlib AST for Python: modules, imports, FastAPI routes, SQLAlchemy
tables; optional `npx madge` for TS/TSX) + directory-based community clustering +
self-contained cytoscape HTML + an architecture-drift audit. Optional LLM enrichment
(--enrich) routes a summary request through the LiteLLM `role-architect` alias.

Dependency-light: Python stdlib only; `npx madge` used if available; LLM optional.

Usage:
  python build_graph.py --root . --backend backend/app --frontend frontend/src \
      --decisions LOCKED-DECISIONS.md --out codegraph [--check] [--enrich]

--check  : exit 1 if any ERROR-level drift violation is found (CI gate).
--enrich : best-effort LLM enrichment of community summaries (never fails the build).
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

BANNED_DEFAULT = {"supabase", "pgvector"}  # extended from the decisions file


# ── Python static extraction ─────────────────────────────────────────────
def py_module_id(root: Path, path: Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    return ".".join(rel.parts)


def scan_python(root: Path, backend: Path):
    nodes, edges = {}, []
    module_ids = set()
    files = sorted(backend.rglob("*.py"))
    for f in files:
        if "__pycache__" in f.parts:
            continue
        module_ids.add(py_module_id(root, f))
    for f in files:
        if "__pycache__" in f.parts:
            continue
        mid = py_module_id(root, f)
        community = _py_community(root, backend, f)
        nodes[mid] = {"id": mid, "type": "module", "file": str(f.relative_to(root)), "community": community}
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        except (SyntaxError, UnicodeDecodeError):
            continue
        # imports (internal only)
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and n.module:
                tgt = n.module
            elif isinstance(n, ast.Import):
                for a in n.names:
                    _add_import_edge(edges, mid, a.name, module_ids)
                continue
            else:
                continue
            _add_import_edge(edges, mid, tgt, module_ids)
        # FastAPI routes + SQLAlchemy tables
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in n.decorator_list:
                    ep = _route_from_decorator(dec)
                    if ep:
                        nid = f"{ep}"
                        nodes[nid] = {"id": nid, "type": "endpoint", "file": nodes[mid]["file"], "community": community}
                        edges.append({"src": mid, "dst": nid, "rel": "exposes"})
            if isinstance(n, ast.ClassDef):
                tbl = _tablename(n)
                if tbl:
                    nid = f"table:{tbl}"
                    nodes[nid] = {"id": nid, "type": "table", "file": nodes[mid]["file"], "community": "data"}
                    edges.append({"src": mid, "dst": nid, "rel": "defines"})
    return nodes, edges, module_ids


def _py_community(root: Path, backend: Path, f: Path) -> str:
    rel = f.relative_to(backend)
    return rel.parts[0] if len(rel.parts) > 1 else "_root"


def _add_import_edge(edges, src, target, module_ids):
    if not target:
        return
    # internal if the target (or a prefix) matches a scanned module
    parts = target.split(".")
    for i in range(len(parts), 0, -1):
        cand = ".".join(parts[:i])
        if cand in module_ids:
            if cand != src:
                edges.append({"src": src, "dst": cand, "rel": "imports"})
            return


def _route_from_decorator(dec):
    if not isinstance(dec, ast.Call):
        return None
    func = dec.func
    if not isinstance(func, ast.Attribute):
        return None
    method = func.attr.lower()
    if method not in {"get", "post", "put", "patch", "delete"}:
        return None
    obj = func.value
    name = getattr(obj, "id", getattr(obj, "attr", ""))
    if name not in {"app", "router", "api_router", "r"}:
        return None
    path = ""
    if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
        path = dec.args[0].value
    return f"{method.upper()} {path}" if path else None


def _tablename(cls: ast.ClassDef):
    for stmt in cls.body:
        if isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                if isinstance(t, ast.Name) and t.id == "__tablename__":
                    if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                        return stmt.value.value
    return None


# ── Frontend (TS/TSX) via madge ───────────────────────────────────────────
def scan_frontend(root: Path, frontend: Path):
    nodes, edges = {}, []
    if not frontend.exists():
        return nodes, edges
    try:
        out = subprocess.run(
            ["npx", "--yes", "madge", "--json", "--extensions", "ts,tsx,js,jsx", str(frontend)],
            capture_output=True, text=True, timeout=180, cwd=str(root),
        )
        data = json.loads(out.stdout) if out.stdout.strip().startswith("{") else {}
    except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError, OSError):
        return nodes, edges  # madge unavailable — skip frontend gracefully
    for fpath, deps in data.items():
        nid = "fe:" + fpath
        comm = "fe:" + (fpath.split("/")[0] if "/" in fpath else "root")
        nodes[nid] = {"id": nid, "type": "frontend", "file": str((frontend / fpath)), "community": comm}
        for d in deps:
            did = "fe:" + d
            edges.append({"src": nid, "dst": did, "rel": "imports"})
    for e in edges:
        nodes.setdefault(e["dst"], {"id": e["dst"], "type": "frontend", "file": e["dst"], "community": "fe:dep"})
    return nodes, edges


# ── Drift audit ────────────────────────────────────────────────────────────
def load_banned(decisions: Path):
    banned = set(BANNED_DEFAULT)
    if decisions.exists():
        for line in decisions.read_text(encoding="utf-8", errors="ignore").splitlines():
            if re.search(r"\bREMOVED\b|\bno\s+supabase\b|\bNOT\s+used\b|KULLANILMAZ", line, re.I):
                for tok in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", line):
                    t = tok.lower()
                    if t in {"supabase", "pgvector", "nginx"}:
                        banned.add(t)
    return banned


def audit(root: Path, backend: Path, frontend: Path, nodes, edges, banned):
    violations = []
    # 1) banned tech used in imports (errors)
    src_files = list(backend.rglob("*.py"))
    for f in src_files:
        if "__pycache__" in f.parts:
            continue
        try:
            txt = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for b in banned:
            if re.search(rf"^\s*(import|from)\s+\S*{re.escape(b)}", txt, re.M | re.I):
                violations.append({"level": "error", "rule": "banned-tech",
                                   "detail": f"{f.relative_to(root)} imports banned '{b}' (removed in LOCKED-DECISIONS)"})
    # 2) frontend -> backend layering (errors)
    for n in nodes.values():
        if n["type"] == "frontend" and re.search(r"(^|/)backend/|backend\.app", n["id"]):
            violations.append({"level": "error", "rule": "layering",
                               "detail": f"frontend imports backend internals: {n['id']}"})
    # 3) import cycles among python modules (warnings)
    adj = defaultdict(set)
    pyids = {n["id"] for n in nodes.values() if n["type"] == "module"}
    for e in edges:
        if e["rel"] == "imports" and e["src"] in pyids and e["dst"] in pyids:
            adj[e["src"]].add(e["dst"])
    for cyc in _cycles(adj):
        violations.append({"level": "warning", "rule": "import-cycle",
                           "detail": "cycle: " + " -> ".join(cyc + [cyc[0]])})
    return violations


def _cycles(adj):
    # Tarjan SCC; report components of size > 1
    index = {}; low = {}; onstack = {}; stack = []; out = []; counter = [0]
    def strong(v):
        index[v] = low[v] = counter[0]; counter[0] += 1
        stack.append(v); onstack[v] = True
        for w in adj.get(v, ()):
            if w not in index:
                strong(w); low[v] = min(low[v], low[w])
            elif onstack.get(w):
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop(); onstack[w] = False; comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                out.append(comp)
    sys.setrecursionlimit(10000)
    for v in list(adj):
        if v not in index:
            strong(v)
    return out


# ── Optional LLM enrichment (best-effort, never fails) ──────────────────────
def enrich(communities, banned):
    base = os.environ.get("LITELLM_API_BASE") or "http://localhost:4000"
    key = os.environ.get("LITELLM_API_KEY", "")
    if not key or key == "sk-1234":
        return {}
    import urllib.request
    prompt = ("You are an architecture reviewer. Given these code communities (name: node count), "
              "give a one-line purpose for each as JSON {community: purpose}. Communities: "
              + json.dumps({c: len(v) for c, v in communities.items()}))
    body = json.dumps({"model": "role-architect", "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": 400, "metadata": {"agent_role": "architect"}}).encode()
    try:
        req = urllib.request.Request(base.rstrip("/") + "/v1/chat/completions", data=body,
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        txt = data["choices"][0]["message"]["content"]
        m = re.search(r"\{.*\}", txt, re.S)
        return json.loads(m.group(0)) if m else {}
    except Exception:
        return {}


# ── HTML (self-contained cytoscape) ─────────────────────────────────────────
HTML = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Code Knowledge Graph</title>
<script src="https://cdn.jsdelivr.net/npm/cytoscape@3/dist/cytoscape.min.js"></script>
<style>body{margin:0;font-family:'JetBrains Mono',monospace;background:#020617;color:#e2e8f0}
#h{padding:.8rem 1rem;border-bottom:1px solid #1e293b}#cy{width:100vw;height:calc(100vh - 64px)}
.t{color:#94a3b8;font-size:.8rem}b{color:#22d3ee}</style></head>
<body><div id="h"><b>Code Knowledge Graph</b> &nbsp;<span class="t" id="stat"></span></div>
<div id="cy"></div><script>
const G = __GRAPH_JSON__;
const palette=['#22d3ee','#34d399','#a78bfa','#fbbf24','#fb7185','#60a5fa','#f472b6','#4ade80','#facc15','#c084fc'];
const comms=[...new Set(G.nodes.map(n=>n.community))];
const color=c=>palette[comms.indexOf(c)%palette.length];
const shape=t=>({module:'round-rectangle',endpoint:'diamond',table:'barrel',frontend:'ellipse'}[t]||'ellipse');
document.getElementById('stat').textContent=G.nodes.length+' nodes • '+G.edges.length+' edges • '+comms.length+' communities • drift: '+G.drift.length;
cytoscape({container:document.getElementById('cy'),
 elements:[...G.nodes.map(n=>({data:{id:n.id,label:n.id.split('.').pop(),c:n.community,t:n.type}})),
           ...G.edges.map((e,i)=>({data:{id:'e'+i,source:e.src,target:e.dst,r:e.rel}}))],
 style:[{selector:'node',style:{'background-color':e=>color(e.data('c')),'shape':e=>shape(e.data('t')),
   'label':'data(label)','color':'#cbd5e1','font-size':'7px','width':14,'height':14}},
  {selector:'edge',style:{'width':.6,'line-color':'#334155','target-arrow-color':'#334155',
   'target-arrow-shape':'triangle','arrow-scale':.5,'curve-style':'bezier'}}],
 layout:{name:'cose',animate:false,nodeRepulsion:9000,idealEdgeLength:60}});
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--backend", default="backend/app")
    ap.add_argument("--frontend", default="frontend/src")
    ap.add_argument("--decisions", default="LOCKED-DECISIONS.md")
    ap.add_argument("--out", default="codegraph")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--enrich", action="store_true")
    a = ap.parse_args()

    root = Path(a.root).resolve()
    backend = (root / a.backend)
    frontend = (root / a.frontend)
    out = (root / a.out)
    out.mkdir(parents=True, exist_ok=True)

    nodes, edges = {}, []
    if backend.exists():
        bn, be, _ = scan_python(root, backend)
        nodes.update(bn); edges += be
    fn, fe = scan_frontend(root, frontend)
    nodes.update(fn); edges += fe

    banned = load_banned(root / a.decisions)
    violations = audit(root, backend, frontend, nodes, edges, banned)

    communities = defaultdict(list)
    for n in nodes.values():
        communities[n["community"]].append(n["id"])
    summaries = enrich(communities, banned) if a.enrich else {}

    graph = {"nodes": list(nodes.values()), "edges": edges,
             "communities": {c: ids for c, ids in communities.items()},
             "summaries": summaries, "drift": violations}
    (out / "graph.json").write_text(json.dumps(graph, indent=2))
    (out / "drift-audit.json").write_text(json.dumps(violations, indent=2))
    (out / "graph.html").write_text(HTML.replace("__GRAPH_JSON__", json.dumps(graph)))

    errs = [v for v in violations if v["level"] == "error"]
    warns = [v for v in violations if v["level"] == "warning"]
    print(f"code-knowledge-graph: {len(nodes)} nodes, {len(edges)} edges, "
          f"{len(communities)} communities -> {a.out}/graph.{{json,html}}")
    print(f"drift: {len(errs)} error(s), {len(warns)} warning(s)")
    for v in violations:
        print(f"  [{v['level']}] {v['rule']}: {v['detail']}")
    if a.check and errs:
        print("DRIFT GATE FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
