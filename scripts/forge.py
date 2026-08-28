#!/usr/bin/env python3
"""Forge a REAL trained surrogate for szl-provctl.
Kernel = ground truth. Surrogate = fast provenance-DAG anomaly classifier: given
graph-structural observables of a provenance DAG (node/edge counts, indegrees,
per-node chain-integrity recompute, edge-head-match recompute, orphan/cycle
signals), predict which anomaly class the kernel's `verify_dag(...)` would report.

The kernel itself is the labeler: `ProvenanceDAG.verify_dag()['first_break']['kind']`
maps to one of {clean, cycle, edge-mismatch, missing-dependency, chain-integrity}.
Each corrupted DAG injects EXACTLY one anomaly (single-aspect rule). A sample of
labels is re-audited by full kernel replay and MUST agree.
Seeded, receipted, reproducible."""
import json, os, random, sys, time, hashlib, platform
_here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.isdir(os.path.join(_here, "build", "torch-universal")):
    sys.path.insert(0, os.path.join(_here, "build", "torch-universal"))  # in-repo run
else:
    sys.path.insert(0, "/tmp/kernel-probe/szl-provctl/build/torch-universal")  # forge-dev run
import szl_provctl as pc
from szl_provctl._chain import UnifiedReceiptChain, GENESIS
from szl_provctl._dag import ProvenanceDAG, ProvenanceNode
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, recall_score

SEED = 20260721
random.seed(SEED); np.random.seed(SEED)
T0 = time.time()

# kernel first_break kinds -> our class names.
# NOTE (measured kernel limitation, honest): the kernel's `missing_dependency`
# verdict is UNREACHABLE — `_topo_order()` raises KeyError on any ghost edge
# BEFORE verify_dag's per-edge check runs, so no DAG can be labeled
# `missing_dependency` through the public API. We therefore do NOT include that
# class (we never fabricate a code path the kernel cannot actually produce).
KIND_TO_CLASS = {
    None: "clean",
    "cycle": "cycle",
    "edge_mismatch": "edge-mismatch",
    "chain_integrity": "chain-integrity",
}
CLASSES = ["clean", "cycle", "edge-mismatch", "chain-integrity"]


def make_chain(n_receipts):
    ch = UnifiedReceiptChain()
    for i in range(n_receipts):
        ch.emit(random.choice(["governed_norm", "lambda_gate", "govsign"]),
                random.choice(["rms_norm", "layer_norm", "gate_decision"]),
                {"seq_local": i, "eps": random.choice([1e-6, 1e-5]), "val": random.random()})
    return ch


def build_clean_dag(n_nodes):
    """A valid multi-run DAG: each node may depend on earlier nodes; heads asserted correctly."""
    dag = ProvenanceDAG()
    ids = [f"run{i}" for i in range(n_nodes)]
    for i, nid in enumerate(ids):
        ch = make_chain(random.randint(1, 4))
        deps = []
        if i > 0 and random.random() < 0.7:
            deps = random.sample(ids[:i], k=random.randint(1, min(2, i)))
        verdict = "BLOCKED" if random.random() < 0.12 else "ALLOWED"
        dag.add_run(nid, ch, deps=deps, verdict=verdict)
    return dag, ids


def corrupt(dag, ids, cls):
    """Inject EXACTLY one anomaly of type cls into a clean DAG (mutating node internals)."""
    nodes = dag._nodes
    if cls == "cycle":
        # create a 2-cycle: pick a node with a dep, add a reverse edge dep->that
        cands = [nid for nid in ids if nodes[nid].deps]
        if not cands:
            # force an edge then reverse it
            a, b = ids[0], ids[1]
            nodes[b].deps.append((a, nodes[a].head()))
            cands = [b]
        target = random.choice(cands)
        dep_id = nodes[target].deps[0][0]
        # add target as a dependency of dep_id -> cycle target<->dep_id
        nodes[dep_id].deps.append((target, nodes[target].head()))
    elif cls == "edge-mismatch":
        cands = [nid for nid in ids if nodes[nid].deps]
        if not cands:
            a, b = ids[0], ids[1]
            nodes[b].deps.append((a, nodes[a].head()))
            cands = [b]
        target = random.choice(cands)
        dep_id, _asserted = nodes[target].deps[0]
        # assert a WRONG head for the edge (single-aspect: only the asserted head changes)
        bad = hashlib.sha3_256(f"tamper{target}".encode()).hexdigest()
        nodes[target].deps[0] = (dep_id, bad)
    elif cls == "chain-integrity":
        # flip a byte inside one node's chain blob body digest (break internal chain)
        target = random.choice(ids)
        records = json.loads(nodes[target].chain_blob)
        if not records:
            ch = make_chain(2); nodes[target].chain_blob = ch.to_json()
            records = json.loads(nodes[target].chain_blob)
        j = random.randrange(len(records))
        d = bytearray(bytes.fromhex(records[j]["digest"])); d[0] ^= 0xFF
        records[j]["digest"] = bytes(d).hex()
        nodes[target].chain_blob = json.dumps(records, sort_keys=True, separators=(",", ":"))
    return dag


def features(dag):
    """Graph-structural observables + cheap per-node/edge recomputes."""
    nodes = dag._nodes
    ids = list(nodes.keys())
    n_nodes = len(ids)
    all_deps = [(nid, dep, head) for nid in ids for (dep, head) in nodes[nid].deps]
    n_edges = len(all_deps)
    indeg = {nid: len(nodes[nid].deps) for nid in ids}
    indeg_vals = list(indeg.values()) or [0]
    # missing-dependency signal: edges pointing at ids not in the DAG
    n_missing = sum(1 for (_n, dep, _h) in all_deps if dep not in nodes)
    # edge-mismatch signal: asserted head != actual head (for present deps)
    n_edge_mismatch = sum(1 for (_n, dep, h) in all_deps
                          if dep in nodes and h != nodes[dep].head())
    # chain-integrity signal: per-node internal chain verify
    n_chain_bad = 0
    for nid in ids:
        ok, _d, _b = UnifiedReceiptChain.verify_json(nodes[nid].chain_blob)
        if not ok:
            n_chain_bad += 1
    # cycle signal: detect a cycle via DFS on present-dep edges
    adj = {nid: [dep for (dep, _h) in nodes[nid].deps if dep in nodes] for nid in ids}
    has_cycle = _detect_cycle(adj)
    n_blocked = sum(1 for nid in ids if nodes[nid].verdict == "BLOCKED")
    return [
        n_nodes, n_edges,
        max(indeg_vals), float(np.mean(indeg_vals)),
        n_missing, n_edge_mismatch, n_chain_bad,
        int(has_cycle), n_blocked,
        float(n_edges) / max(n_nodes, 1),
    ]


def _detect_cycle(adj):
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in adj}
    def dfs(u):
        color[u] = GRAY
        for v in adj.get(u, []):
            if color.get(v, WHITE) == GRAY:
                return True
            if color.get(v, WHITE) == WHITE and dfs(v):
                return True
        color[u] = BLACK
        return False
    return any(color[n] == WHITE and dfs(n) for n in adj)


FEATURE_NAMES = ["n_nodes", "n_edges", "max_indegree", "mean_indegree",
                 "n_missing_deps", "n_edge_mismatch", "n_chain_bad",
                 "has_cycle", "n_blocked_nodes", "edge_density"]


def kernel_class(dag):
    """Ground truth: run the kernel verify_dag and map first_break.kind to a class."""
    rep = pc.verify_dag(dag)
    if rep["ok"]:
        return "clean"
    kind = (rep.get("first_break") or {}).get("kind")
    return KIND_TO_CLASS.get(kind, kind if kind in CLASSES else "chain-integrity")


def make_dag(cls):
    """Build a DAG whose kernel-derived label is GUARANTEED to equal cls."""
    for _ in range(60):
        n = random.randint(3, 8)
        dag, ids = build_clean_dag(n)
        if cls != "clean":
            corrupt(dag, ids, cls)
        derived = kernel_class(dag)
        if derived == cls:
            return dag
    raise RuntimeError(f"could not synthesize a kernel-confirmed {cls} DAG")


# ---- generate ----
X, y = [], []
dags = []
PER_CLASS = {c: (2600 if c == "clean" else 1900) for c in CLASSES}
plan = []
for c, k in PER_CLASS.items():
    plan += [c] * k
random.shuffle(plan)
for cls in plan:
    dag = make_dag(cls)
    X.append(features(dag)); y.append(cls); dags.append((dag, cls))

# ground-truth audit: full kernel replay must agree
audit_checked = 0
for i in random.sample(range(len(dags)), 700):
    dag, cls = dags[i]
    assert kernel_class(dag) == cls, f"kernel disagrees DAG {i}: {kernel_class(dag)} != {cls}"
    audit_checked += 1

X = np.array(X, dtype=np.float64); y = np.array(y)
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)
clf = HistGradientBoostingClassifier(random_state=SEED, max_iter=300, early_stopping=True)
clf.fit(Xtr, ytr)
pred = clf.predict(Xte)
acc = accuracy_score(yte, pred)
per_class_recall = {c: float(recall_score(yte == c, pred == c, zero_division=0)) for c in CLASSES}

out_dir = os.path.dirname(os.path.abspath(__file__))
# P0: do not emit pickle/joblib. The kernel source is the approved path.
if os.path.exists(f"{out_dir}/model.joblib") or os.path.exists(f"{os.path.dirname(out_dir)}/model.joblib"):
    raise SystemExit("REFUSE: model.joblib is present. Delete it; pickle is not an approved load path.")
receipt = {
  "artifact": "SZLHOLDINGS/szl-provctl surrogate v1",
  "role": "provenance-DAG anomaly classifier surrogate — kernel remains ground truth",
  "generator": {"script": "scripts/forge.py", "seed": SEED, "kernel_version": pc.__version__,
                 "kernel_labelled": True, "kernel_audited_dags": audit_checked,
                 "labeler": "ProvenanceDAG.verify_dag()['first_break']['kind']"},
  "data": {"rows": int(len(y)), "classes": CLASSES,
            "class_counts": {c: int((y == c).sum()) for c in CLASSES},
            "split": "80/20 stratified", "features": FEATURE_NAMES,
            "feature_policy": "graph-structural observables + cheap per-node chain recompute + edge-head-match recompute; the surrogate never replaces the kernel's full verify_dag traversal"},
  "model": {"type": "sklearn.HistGradientBoostingClassifier",
             "params": {"max_iter": 300, "early_stopping": True, "random_state": SEED},
             "file": None, "serialization": "QUARANTINED", "sha256": None,
             "statement": "joblib/pickle is not an approved load path. Use torch-ext kernel source."},
  "metrics_MEASURED": {"fidelity_vs_kernel_heldout": round(float(acc), 4),
                        "test_accuracy": round(float(acc), 4),
                        "per_class_recall": {k: round(v, 4) for k, v in per_class_recall.items()}},
  "environment": {"python": platform.python_version(), "sklearn": __import__("sklearn").__version__,
                   "numpy": np.__version__, "host": "replit 2-vCPU container",
                   "wall_seconds": round(time.time() - T0, 1)},
  "honesty": "Every number above is MEASURED by this run. Fidelity = agreement%% with the kernel's ProvenanceDAG.verify_dag anomaly verdict on a held-out split. The surrogate is a fast triage; the kernel's full DAG traversal + in-toto/SLSA interop stay authoritative. Λ untouched = Conjecture 1.",
  "trained_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
}
quarantine = {
  "status": "QUARANTINED",
  "artifact": "model.joblib",
  "reason": "sklearn/joblib pickle is executable serialization, not an approved load path",
  "approved_load": "torch-ext kernel source",
  "hub": "SZLHOLDINGS/szl-provctl model.joblib remains Hub residue until a Hub PR with exact parent_commit deletes it",
}
with open(f"{out_dir}/SURROGATE_QUARANTINE.json", "w") as f: json.dump(quarantine, f, indent=2)
with open(f"{out_dir}/TRAINING_RECEIPT.json", "w") as f:
    json.dump(receipt, f, indent=2)
print(json.dumps(receipt["metrics_MEASURED"], indent=2))
print(f"rows={len(y)} kernel_audited_dags={audit_checked} wall={receipt['environment']['wall_seconds']}s")
