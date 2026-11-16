"""Source identity and discovery gates for the deterministic matched EFS pool."""

import ast
import copy
import hashlib


def merge_grammar_discoveries(libraries):
    merged = {}
    for seed, library in libraries.items():
        for key, row in library.items():
            if hashlib.sha256(row["code"].encode()).hexdigest() != key:
                raise ValueError("Control factor code identity changed")
            if row["origin"] not in ["paper_seed_family", "programmatic_grammar"]:
                raise ValueError("Control origin substituted")
            date = row["created_index"]
            if (
                not isinstance(date, int)
                or isinstance(date, bool)
                or (row["origin"] == "programmatic_grammar" and date < 0)
            ):
                raise ValueError("Control discovery date invalid")
            if key not in merged:
                merged[key] = {**copy.deepcopy(row), "discoveries": []}
            value = merged[key]
            if value["code"] != row["code"] or value["origin"] != row["origin"]:
                raise ValueError("Conflicting control provenance")
            value["created_index"] = min(value["created_index"], date)
            value["discoveries"].append({"trial": seed, "created_index": date})
    return merged


def financial_block(source):
    tree = ast.parse(source)
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    start = next(
        i
        for i, n in enumerate(main.body)
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "factors" for t in n.targets)
    )
    end = next(
        i
        for i, n in enumerate(main.body[start:], start)
        if isinstance(n, ast.Expr)
        and isinstance(n.value, ast.Call)
        and isinstance(n.value.func, ast.Name)
        and n.value.func.id == "atomic_json"
        and any(isinstance(x, ast.Constant) and x.value == "completion.json" for x in ast.walk(n.value.args[0]))
    )
    nodes = main.body[start:end]
    digest = hashlib.sha256(
        ast.dump(ast.Module(body=nodes, type_ignores=[]), include_attributes=False).encode()
    ).hexdigest()
    return digest, nodes[0].lineno, nodes[-1].end_lineno


def require_same_financial_block(left, right):
    a = financial_block(left)[0]
    b = financial_block(right)[0]
    if a != b:
        raise ValueError("Control and LLM pool financial computations differ")
    return a
