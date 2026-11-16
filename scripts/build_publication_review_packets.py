#!/usr/bin/env python3
# ruff: noqa: E402 - standalone source-path bootstrap
"""Generate source-fidelity packets without exposing new strategy outcomes."""

from pathlib import Path
import sys
import json
import tarfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from alpha_evolve.openrouter_budget import atomic_json, sha256

OUT = ROOT / "paper_runs/publication_upgrade_v1/source_review"
OUT.mkdir(parents=True, exist_ok=True)
CASES = {
    "EFS": {
        "paper": "https://arxiv.org/abs/2507.17211v1",
        "source": "Paper appendix prompts and numerical descriptions; author executable EFS source unavailable",
        "recipe": "paper_runs/economic_fidelity/efs_v1/recipe.json",
        "comparisons": "paper_runs/publication_upgrade_v1/efs_matched_recipe.json",
        "code": [
            "scripts/run_efs_economic_fidelity.py",
            "src/alpha_evolve/economic_fidelity.py",
            "scripts/run_efs_matched_search.py",
        ],
        "scope": "Paper-guided price-factor evolution at daily cadence, not recovered author code",
        "preserved": "US50 identities,12 seed families, weekly mutation/crossover requests, m25 search feedback, m10 sparse equal-weight trading",
        "differences": "JKP daily prices replace vendor snapshot; current GPT4.1; explicit60-session feedback and warmup, pool/pruning conventions and next-close execution; one LLM trajectory",
        "review_focus": "Assess the m10/m25 interpretation, source equations, signal formation versus executable return horizon, and whether the fixed grammar is a fair bounded control.",
    },
    "FinMem": {
        "paper": "https://arxiv.org/abs/2311.13743",
        "source": "https://github.com/pipiku915/finmem-llm-stocktrading/tree/be814aa47970de9bf2fdd6a1d5a60ae5cf361b46",
        "recipe": "paper_runs/publication_upgrade_v1/finmem_recipe.json",
        "code": [
            "scripts/run_finmem_economic_fidelity.py",
            "scripts/prepare_finmem_fidelity_inputs.py",
            "scripts/run_finmem_fidelity_python.sh",
            "environment_specs/tokenizer_cache.json",
        ],
        "scope": "Released actor, layered memory, portfolio feedback and embedding wrapper, with alternative dated inputs",
        "preserved": "Four memory stores, native ranking/decay/promotions/access feedback, paper topK5 and temperature0.7, GPT4Turbo route, source Ada002 embedding path",
        "differences": "TSLA-only/one seed; missing replacement news beforeMay2022; source profile and alternative filings/news; paper score is not NAV; a separate cash/stock economic adapter is explicit",
        "review_focus": "Check terminal-date handling, no test future label, source score versus cumulative one-share feedback versus investable portfolio, and cardinality-matched semantic retrieval.",
    },
    "FinAgent": {
        "paper": "https://arxiv.org/abs/2402.18485",
        "source": "https://github.com/DVampire/FinAgent",
        "recipe": "paper_runs/publication_upgrade_v1/finagent_recipe.json",
        "code": [
            "scripts/run_finagent_economic_fidelity.py",
            "scripts/resume_finagent_after_transport_failure.py",
            "scripts/run_finmem_fidelity_python.sh",
            "environment_specs/tokenizer_cache.json",
            "src/alpha_evolve/publication_embeddings.py",
            "scripts/prepare_publication_dated_inputs.py",
        ],
        "scope": "Released five-stage actor and complete prompt variant, with causal validation/account repairs",
        "preserved": "Actual vision calls; source train/valid full-tool templates; source diverse queries and FAISS memory; source text-embedding-3-large3072-dimensional provider; original whole-share buy/sell rules",
        "differences": "Current GPT4o and study temperature0.1 replace unavailable historical model IDs and the release provider temperature default1.0; alternative data; Matplotlib charts; missing guidance/economics; current-close accounting repair",
        "review_focus": "Verify full-tool template selection, source embedding model/dimensions/token-ID path, training price cutoff, no future validation chart, fills before current-account observation, and retrieval ablation scope.",
    },
    "TradingAgents": {
        "paper": "https://arxiv.org/abs/2412.20138v7",
        "source": "https://github.com/TauricResearch/TradingAgents/tree/cc97cb6d5deb10eac370db0c6678e2796a62eba8",
        "recipe": "paper_runs/publication_upgrade_v1/tradingagents_recipe.json",
        "code": ["scripts/run_tradingagents_economic_fidelity.py", "scripts/prepare_publication_dated_inputs.py"],
        "scope": "Released graph and roles with frozen historical tools and an explicit economic account",
        "preserved": "Four analyst factories, bull/bear discussion, research manager, trader, risk discussion/judge, categorical signal extraction and original graph routing",
        "differences": "Current GPT4o/.1 for both model roles; AAPL-only paper quarter; absent Reddit/insider data; SEC summaries replace SimFin; release has no executable portfolio sizing/fills; empty memories remain empty",
        "review_focus": "Assess dated tool clamps, information equality across controls, and source investment_plan wiring. It is the research-manager plan, despite the source judge calling it the trader plan.",
    },
    "GuruAgents": {
        "paper": "https://arxiv.org/abs/2510.01664",
        "source": "https://github.com/yejining99/GuruAgents/tree/74ad2e6ce2e604c73a6fc2829d48ab58fe6be050",
        "recipe": "paper_runs/publication_upgrade_v1/guruagents_recipe.json",
        "code": [
            "scripts/run_guruagents_openrouter_replay.py",
            "scripts/build_publication_control_accounts.py",
            "scripts/evaluate_guruagents_prompt_replay_performance.py",
        ],
        "scope": "Actual source-prompt/tool replays with corrected quarterly execution accounts",
        "preserved": "Five investor roles, original prompts and archived financial tool observations, GPT4o/temperature0, source normalization of percentage weights",
        "differences": "Archived inputs lack full publication-vintage evidence; source ticker repairs retained; first post-quarter close and90-day lag stress; researcher equal-weight role ensemble is not a paper headline portfolio",
        "review_focus": "Check relative-weight normalization in the original notebook, formation/filing availability, drift between quarters, same-information one-call control, and price/fee conventions.",
    },
    "QuantaAlpha": {
        "paper": "https://arxiv.org/abs/2602.07085v3",
        "source": "https://github.com/QuantaAlpha/QuantaAlpha",
        "recipe": "paper_runs/publication_upgrade_v1/quantaalpha_recipe.json",
        "code": ["scripts/export_quantaalpha_economic_fidelity.py", "scripts/rerun_quantaalpha_complete_pool.py"],
        "scope": "Released factor-library, predictor and portfolio execution, not fresh agent search",
        "preserved": "Complete150 custom expressions plus20 core factors, native LightGBM split/training, CSI300 Top50/drop5 and native execution/cost settings",
        "differences": "One explicit MEAN broadcasting repair; reconstructed environment; unavailable generator trace and historical factor selection; local experiment-logging backend adaptation",
        "review_focus": "Confirm component-level scope, benchmark-relative native metric definition, complete-pool lineage, and that this Chinese native account is not presented as a US JKP132 test.",
    },
}
now = datetime.now(timezone.utc).isoformat()
catalog = []
for case, info in CASES.items():
    recipe_path = ROOT / info["recipe"]
    recipe = json.loads(recipe_path.read_text())
    fingerprints = {name: sha256(ROOT / name) for name in info["code"]}
    fingerprints[info["recipe"]] = sha256(recipe_path)
    if "comparisons" in info:
        fingerprints[info["comparisons"]] = sha256(ROOT / info["comparisons"])
    lines = [
        f"# {case}: outcome-free source-fidelity review packet",
        "",
        "This packet contains no new strategy return, alpha, ranking, or significance result.",
        "",
        f"Paper: {info['paper']}",
        f"Source: {info['source']}",
        "",
        f"Claimed scope: {info['scope']}.",
        "",
        f"Preserved elements: {info['preserved']}.",
        "",
        f"Declared substitutions/repairs: {info['differences']}.",
        "",
        f"Reviewer focus: {info['review_focus']}",
        "",
        "A reviewer should assess the conditional mechanism comparison represented here. Full original-paper reproduction, original-vintage inputs, and historical model equivalence are not claimed.",
        "",
        "| Review dimension | Required judgment |",
        "|---|---|",
        "| Information | Is all supplied information available by the decision time under the disclosed data assumptions? |",
        "| Mechanism | Does the claimed critical mechanism actually execute, including model calls where required? |",
        "| Economics | Are action, position, cash, execution, turnover and fee definitions coherent? |",
        "| Control | Is the primary comparison matched on the information/constraints it claims to match? |",
        "| Claim boundary | Are the substitutions and missing source elements compatible with the stated conditional claim? |",
        "",
        "## Files and hashes",
        "",
        "| File | SHA-256 |",
        "|---|---|",
    ]
    for name, value in fingerprints.items():
        lines.append(f"| `{name}` | `{value}` |")
    lines += [
        "",
        "## Human review record",
        "",
        "Use the accompanying JSON template and record it with `scripts/record_publication_human_review.py`. Automated tests are separate evidence and do not fill any human review field. A review of a changed packet must be renewed.",
        "",
    ]
    packet = OUT / f"{case}_SOURCE_REVIEW.md"
    packet.write_text("\n".join(lines))
    packet_hash = sha256(packet)
    template = {
        "case": case,
        "packet_sha256": packet_hash,
        "reviewer_name": None,
        "reviewer_relationship_to_implementation": None,
        "independent_of_implementation": None,
        "reviewed_at_utc": None,
        "verdict": None,
        "allowed_verdicts": [
            "approved_for_conditional_mechanism_comparison",
            "changes_required",
            "not_economically_comparable",
        ],
        "judgments": {
            dimension: None for dimension in ["information", "mechanism", "economics", "control", "claim_boundary"]
        },
        "required_changes": [],
        "human_attestation": None,
    }
    atomic_json(OUT / f"{case}_REVIEW_TEMPLATE.json", template)
    catalog.append(
        {
            "case": case,
            **info,
            "packet": str(packet.relative_to(ROOT)),
            "packet_sha256": packet_hash,
            "recipe_sha256": sha256(recipe_path),
            "implementation_sha256": fingerprints,
        }
    )
atomic_json(
    OUT / "packet_manifest.json", {"generated_at_utc": now, "packets": catalog, "contains_strategy_outcomes": False}
)
ledger_path = OUT / "human_review_ledger.json"
ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {"reviews": []}
ledger["current_packets"] = {row["case"]: row["packet_sha256"] for row in catalog}


def approved(case, packet):
    latest = {}
    for record in ledger["reviews"]:
        if record.get("case") == case and record.get("packet_sha256") == packet:
            latest[record["reviewer_name"].strip().casefold()] = record
    return bool(latest) and all(
        record.get("verdict") == "approved_for_conditional_mechanism_comparison"
        and record.get("independent_of_implementation") is True
        for record in latest.values()
    )


ledger["independent_human_review_complete"] = all(
    approved(case, packet) for case, packet in ledger["current_packets"].items()
)
atomic_json(ledger_path, ledger)
(OUT / "README.md").write_text(
    "# Independent source review\n\nSix outcome-free packets are ready. No human review has been inferred from tests or generated by the assistant. The ledger retains every submitted review, including requested changes, and only current matching packet hashes can satisfy the gate.\n\n"
    + "\n".join(
        f"- [{row['case']}]({row['case']}_SOURCE_REVIEW.md) | [review template]({row['case']}_REVIEW_TEMPLATE.json)"
        for row in catalog
    )
    + "\n"
)
print("SOURCE_PACKETS_READY", len(catalog), "human_review_complete", ledger["independent_human_review_complete"])

# A separate source-only bundle supports outcome-blind review. No result tables,
# model responses, raw inputs or report builders are included.
bundle_files = {
    "docs/PUBLICATION_UPGRADE_PROTOCOL.md",
    "scripts/build_publication_review_packets.py",
    "scripts/record_publication_human_review.py",
    "src/alpha_evolve/economic_fidelity.py",
    "src/alpha_evolve/openrouter_budget.py",
    "src/alpha_evolve/publication_economics.py",
    "src/alpha_evolve/publication_embeddings.py",
    "src/alpha_evolve/publication_llm.py",
    "src/alpha_evolve/publication_portfolio.py",
    "src/alpha_evolve/publication_replay.py",
}
for packet in catalog:
    bundle_files.update(packet["implementation_sha256"])
bundle_files.update(str(p.relative_to(ROOT)) for p in OUT.iterdir() if p.is_file() and p.name != "bundle_manifest.json")
bundle = ROOT / "artifacts/publication_upgrade_v1/outcome_free_source_review_bundle.tar.gz"
with tarfile.open(bundle, "w:gz", compresslevel=6) as tar:
    for name in sorted(bundle_files):
        tar.add(ROOT / name, arcname=name, recursive=False)
atomic_json(
    OUT / "bundle_manifest.json",
    {
        "bundle": str(bundle.relative_to(ROOT)),
        "sha256": sha256(bundle),
        "bytes": bundle.stat().st_size,
        "files": {name: sha256(ROOT / name) for name in sorted(bundle_files)},
        "contains_strategy_outcomes": False,
    },
)
print("OUTCOME_FREE_REVIEW_BUNDLE_READY", bundle)
