"""Strict identities for secondary native libraries and explicit baseline reuse."""

import hashlib
import json
from alpha_evolve.openrouter_budget import sha256


def expected_units(case):
    if case not in ("quantaalpha", "alphaagent"):
        raise ValueError("Unknown case")
    return list(range(7)) if case == "quantaalpha" else list(range(1, 21))


def require_secondary_library(case, library, unit, private):
    if unit not in expected_units(case):
        raise ValueError("Unplanned secondary unit")
    name = "quantaalpha_bounded" if case == "quantaalpha" else f"alphaagent_rounds_paper_gpt35_{unit:02d}"
    selected = unit if case == "quantaalpha" else None
    if library["case"] != case or set(library["source_manifests"]) != {name}:
        raise ValueError("Secondary source trial substituted")
    if library.get("experiment_index_filter") != selected:
        raise ValueError("Secondary experiment filter changed")
    path = private / name / "used_factor_manifest.json"
    if sha256(path) != library["source_manifests"][name]:
        raise ValueError("Secondary source-used manifest changed")
    manifest = json.loads(path.read_text())
    allowed = {r["index"] for r in manifest["experiments"] if r.get("within_first_five_rounds", True)}
    if selected is not None:
        if selected not in allowed:
            raise ValueError("Planned source task absent")
        allowed = {selected}
    required = {r["sha256"] for r in manifest["programs"] if any(u["experiment_index"] in allowed for u in r["uses"])}
    actual = [r["code_sha256"] for r in library["programs"]]
    if not required or set(actual) != required or len(actual) != len(set(actual)):
        raise ValueError("Secondary library drops or substitutes source-used programs")
    if case == "alphaagent":
        from alpha_constructor_abort_v3 import validate_five as validate_alpha_five_attempts
        validate_alpha_five_attempts(private / name)


def require_parent_subset(library, parent, parent_digest):
    if library.get("reused_program_library_manifest_sha256") != parent_digest:
        raise ValueError("Secondary library is not bound to the fixed complete parent")
    for key in ("case", "data_sha256", "membership_sha256"):
        if library[key] != parent[key]:
            raise ValueError("Secondary inputs or universe differ from common baseline")
    complete = {r["code_sha256"]: r for r in parent["programs"]}
    for row in library["programs"]:
        source = complete.get(row["code_sha256"])
        if source is None or any(row[k] != source[k] for k in ("data_sha256", "output_sha256", "expression")):
            raise ValueError("Secondary program differs from complete parent columns")


def validate_library(path, root, private):
    manifest = json.loads(path.read_text())
    folder = path.parent
    for name, key in [("fixed_factors.parquet", "matrix_sha256"), ("fixed_factors.pkl", "pickle_sha256")]:
        if sha256(folder / name) != manifest[key]:
            raise ValueError("Fixed library matrix changed")
    source = (
        private / "dependencies" / ("alphaagent_95e478" if manifest["case"] == "alphaagent" else "quantaalpha_b7ceb27")
    )
    hashes = {str(p.relative_to(source)): sha256(p) for p in sorted(source.rglob("*.py"))}
    source_digest = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    evidence = {
        "library_sha256": sha256(path),
        "source_python_sha256": source_digest,
        "source_gates": {},
        "program_proofs": {},
    }
    programs = {}
    for name, digest in manifest["source_manifests"].items():
        run = private / name
        used = run / "used_factor_manifest.json"
        if sha256(used) != digest:
            raise ValueError("Used source manifest changed")
        programs.update({row["sha256"]: row for row in json.loads(used.read_text())["programs"]})
        evidence["source_gates"][name] = {}
        for gate in ("full_replay_validation.json", "independent_accounts/validation.json"):
            p = run / gate
            if json.loads(p.read_text())["status"] != "pass":
                raise ValueError("Source replay/account gate failed")
            evidence["source_gates"][name][gate] = sha256(p)
    for row in manifest["programs"]:
        digest = row["code_sha256"]
        if sha256(root / programs[digest]["code"]) != digest:
            raise ValueError("Actual source-used code changed")
        if sha256(folder / (digest + ".parquet")) != row["output_sha256"]:
            raise ValueError("Materialized program column changed")
        accepted = []
        for name in row["source_runs"]:
            if name not in manifest["source_manifests"]:
                raise ValueError("Unexpected program source run")
            p = private / name / "causality_full_universe" / (digest + ".json")
            if p.exists():
                proof = json.loads(p.read_text())
                if (
                    proof["status"] == "pass"
                    and proof["code_sha256"] == digest
                    and proof["input_sha256"] == manifest["data_sha256"]
                    and proof["source_python_sha256"] == source_digest
                ):
                    accepted.append({"path": str(p.relative_to(root)), "sha256": sha256(p)})
        if not accepted:
            raise ValueError("Nonvacuous full-universe causality gate missing")
        evidence["program_proofs"][digest] = accepted
    return manifest, evidence


def require_complete_panel(case, units):
    if sorted(units) != expected_units(case):
        raise ValueError("Incomplete secondary panel; no successful-only subset or duplicate units")


def validate_execution_identity(run_name, execution, private):
    run = private / run_name
    recipe = json.loads((run / "execution_recipe.json").read_text())
    marker = recipe.get("execution_sensitivity")
    if execution == "native":
        if marker is not None or run_name.endswith("_open_information"):
            raise ValueError("Opening sensitivity substituted for native diagnostic")
        return {"execution_identity": "native"}
    if execution != "opening_information" or marker != "opening_information_limit_proxy":
        raise ValueError("Native execution cannot stand in for opening-information eligibility")
    if not run_name.endswith("_open_information") or recipe["source_run"] != run_name.removesuffix("_open_information"):
        raise ValueError("Opening source identity changed")
    source = private / recipe["source_run"]
    if sha256(source / "execution_recipe.json") != recipe["source_execution_recipe_sha256"]:
        raise ValueError("Original prediction-run recipe changed")
    evidence = {"execution_identity": "opening_information", "source_run": recipe["source_run"]}
    for name, key in [("pred.pkl", "source_prediction_sha256"), ("label.pkl", "source_label_sha256")]:
        for folder in (run, source):
            paths = list(folder.glob("mlruns/*/*/artifacts/" + name))
            if len(paths) != 1 or sha256(paths[0]) != recipe[key]:
                raise ValueError("Saved prediction/label identity changed")
        evidence[key] = recipe[key]
    done = json.loads((run / "completion.json").read_text())
    if not done["predictions_byte_identical"] or done["retrained"] or done["new_model_calls"] != 0:
        raise ValueError("Opening sensitivity changed predictions or refit the model")
    return evidence
