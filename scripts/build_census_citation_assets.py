#!/usr/bin/env python3
"""Build the complete screened-corpus bibliography and manuscript citation macros."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import re
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
PROHIBITED = ("López de Prado", "Lopez de Prado", "LopezDePrado")

# Frozen crosswalk from the source-level reconstruction ledger to the canonical
# scholarly works in the 98-work census. These 40 works produce 50 retained-
# corpus mappings; the remaining 12 mappings come from non-retained diagnostics.
MAPPING_SOURCE_TO_WORK_ID = {
    "EFS": "CensusArxiv250717211",
    "AlphaAgent": "CensusArxiv250216789",
    "QuantaAlpha": "CensusArxiv260207085",
    "QuantEvolver": "CensusArxiv260515412",
    "R&D-Agent-Quant": "CensusArxiv250514738",
    "Alpha-Jungle": "CensusArxiv250511122",
    "FactorMiner": "CensusArxiv260214670",
    "CogAlpha": "CensusArxiv251118850",
    "FAMA": "CensusACL2024findingsacl233",
    "Alpha-GPT": "WorkAlphaGPT",
    "Alpha-GPT 2.0": "CensusArxiv240209746",
    "Chain-of-Alpha": "CensusArxiv250806312",
    "FactorMAD": "CensusDOI10114537682923770377",
    "AlphaLogics": "CensusArxiv260320247",
    "AlphaAgentEvo": "CensusORlNmZrawUMu",
    "Alpha-R1": "CensusArxiv251223515",
    "AlphaCrafter": "CensusArxiv260505580",
    "LLMFactor": "CensusArxiv240610811",
    "FactorEngine": "CensusArxiv260316365",
    "TradingAgents": "CensusArxiv241220138",
    "ContestTrade": "CensusArxiv250800554",
    "QuantAgent HFT": "CensusArxiv250909995",
    "QuantAgent Holy Grail": "CensusArxiv240203755",
    "AlphaQuanter": "CensusACL2026findingsacl456",
    "FinMem": "CensusArxiv231113743",
    "FinCon": "CensusArxiv240706567",
    "FinAgent": "CensusArxiv240218485",
    "FLAG-Trader": "CensusACL2025findingsacl716",
    "MM-DREX": "CensusArxiv250905080",
    "Trading-R1": "CensusArxiv250911420",
    "Janus-Q": "CensusArxiv260219919",
    "Trade in Minutes": "CensusArxiv251004787",
    "AlphaAgents": "CensusArxiv250811152",
    "MarketSenseAI 2.0": "CensusArxiv250200415",
    "MountainLion": "CensusArxiv250720474",
    "P1GPT": "CensusArxiv251023032",
    "FinVision": "CensusArxiv241108899",
    "GuruAgents": "CensusArxiv251001664",
    "QuantAgents": "CensusArxiv251004643",
    "HedgeAgents": "CensusArxiv250213165",
}
SOURCE_GROUNDED_WORK_IDS = {
    "CensusArxiv250717211", "CensusArxiv260515412", "CensusArxiv250511122",
    "CensusACL2024findingsacl233", "CensusArxiv251001664",
}
RETAINED_DIRECT_WORK_IDS = {
    "CensusArxiv250216789", "CensusArxiv250800554", "CensusArxiv240706567",
    "CensusArxiv251001664", "CensusArxiv250909995", "CensusArxiv260515412",
    "CensusArxiv250514738", "CensusArxiv250911420",
}
DIAGNOSTIC_DIRECT_WORK_IDS = {
    "CensusWebalphabenchcc", "CensusArxiv260218481", "CensusArxiv260211917",
    "CensusArxiv250511065", "CensusArxiv251103628", "CensusArxiv251202261",
}


def read_csv(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream, delimiter=delimiter))


def normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def registry_row_for_mapping(
    registry: list[dict[str, str]], source_index: str, source_name: str
) -> dict[str, str]:
    target_index = str(int(source_index))
    candidates = [
        row
        for row in registry
        if target_index
        in {str(int(value)) for value in re.findall(r"\d+", row["old_refs"])}
    ]
    if len(candidates) > 1:
        target_name = normalized_name(source_name)
        candidates = [
            row
            for row in candidates
            if target_name in normalized_name(row["system_name"])
            or normalized_name(row["system_name"]) in target_name
        ]
    require(
        len(candidates) == 1,
        f"mapping source does not resolve to one screened lineage: {source_name}",
    )
    return candidates[0]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def normalized_urls(registry: Iterable[dict[str, str]]) -> set[str]:
    return {
        url.strip()
        for row in registry
        for url in row["primary_record"].split(" ; ")
        if url.strip()
    }


def latex_text(value: str) -> str:
    value = re.sub(r"\s*\([^)]*[^\x00-\x7f][^)]*\)", "", value)
    replacements = {
        "‑": "-", "–": "--", "—": "---", "“": "``", "”": "''", "’": "'",
        "ü": r"{\"u}", "&": r"\&", "%": r"\%", "#": r"\#", "_": r"\_",
    }
    return "".join(replacements.get(char, char) for char in value)


def bibtex_entry(row: dict[str, str]) -> str:
    authors = " and ".join(latex_text(author.strip()) for author in row["authors"].split(";") if author.strip())
    lines = [f"@{row['entry_type']}{{{row['bibtex_key']},", f"  author = {{{authors}}},",
             f"  title = {{{{{latex_text(row['title'])}}}}},", f"  year = {{{row['year']}}},"]
    if row["entry_type"] == "inproceedings":
        lines.append(f"  booktitle = {{{latex_text(row['venue'])}}},")
    elif row["entry_type"] == "article":
        lines.append(f"  journal = {{{latex_text(row['venue'])}}},")
    elif row["venue"] == "arXiv":
        lines.extend([
            f"  eprint = {{{row['source_identifier']}}},",
            "  archivePrefix = {arXiv},",
        ])
        if row["primary_class"]:
            lines.append(f"  primaryClass = {{{row['primary_class']}}},")
    if "doi.org/" in row["primary_url"]:
        lines.append(f"  doi = {{{row['primary_url'].split('doi.org/', 1)[1]}}},")
    lines.append(f"  url = {{{row['primary_url']}}}")
    lines.append("}")
    return "\n".join(lines)


def citation_macro(name: str, keys: list[str]) -> str:
    return f"\\newcommand{{\\{name}}}{{\\cite{{{','.join(sorted(keys))}}}}}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    registry = read_csv(root / "literature_review/census_v1/system_registry.csv", delimiter="|")
    metadata = read_csv(root / "literature_review/census_v1/primary_record_metadata.csv")

    require(len(registry) == 103, "pre-trim lineage count changed")
    require(sum(row["main_FT"] == "Y" for row in registry) == 67, "retained F/T lineage count changed")
    require(len(metadata) == 104, "primary-record link count changed")
    require({row["primary_url"] for row in metadata} == normalized_urls(registry),
            "metadata URLs do not exactly cover the screened registry")
    require(len({row["canonical_work_id"] for row in metadata}) == 98,
            "canonical pre-trim work count changed")
    require(sum(row["main_ft"] == "yes" for row in metadata) == 71,
            "retained primary-record link count changed")
    require(len({row["canonical_work_id"] for row in metadata if row["main_ft"] == "yes"}) == 69,
            "retained canonical work count changed")
    require(len({row["bibtex_key"] for row in metadata}) == len(metadata), "duplicate BibTeX key")
    for field in ("title", "authors", "year", "venue", "metadata_source"):
        require(all(row[field].strip() for row in metadata), f"missing metadata field: {field}")
    for work_id in {row["canonical_work_id"] for row in metadata}:
        preferred = [row for row in metadata if row["canonical_work_id"] == work_id
                     and row["preferred_citation"] == "yes"]
        require(len(preferred) == 1, f"canonical work must have exactly one preferred record: {work_id}")
    joined = "\n".join("|".join(row.values()) for row in metadata)
    require(not any(name.casefold() in joined.casefold() for name in PROHIBITED),
            "prohibited author appears in corpus metadata")

    preferred = sorted((row for row in metadata if row["preferred_citation"] == "yes"),
                       key=lambda row: (row["authors"].split(";")[0], row["year"], row["title"]))
    bibliography = "% Generated by scripts/build_census_citation_assets.py; do not edit by hand.\n\n"
    bibliography += "\n\n".join(bibtex_entry(row) for row in preferred) + "\n"
    (root / "docs/paper/census_primary_records.bib").write_text(bibliography, encoding="utf-8")

    retained = [row for row in preferred if row["main_ft"] == "yes"]
    excluded = [row for row in preferred if row["main_ft"] == "no"]
    formula_rows = [row for row in retained if "F" in row["strata"].split("; ")]
    trading_rows = [row for row in retained if "T" in row["strata"].split("; ")]
    formula_keys = [row["bibtex_key"] for row in formula_rows]
    trading_keys = [row["bibtex_key"] for row in trading_rows]
    require(len(formula_keys) + len(trading_keys) == 69, "retained works are not partitioned into F/T")
    macro_lines = [
        "% Generated by scripts/build_census_citation_assets.py; do not edit by hand.",
        r"\newcommand{\PretrimLineageCount}{103\xspace}",
        r"\newcommand{\PretrimWorkCount}{98\xspace}",
        r"\newcommand{\RetainedLineageCount}{67\xspace}",
        r"\newcommand{\RetainedWorkCount}{69\xspace}",
        r"\newcommand{\ExcludedWorkCount}{29\xspace}",
        r"\newcommand{\ReconstructedWorkCount}{40\xspace}",
        r"\newcommand{\AvailabilityOnlyWorkCount}{29\xspace}",
        r"\newcommand{\RetainedMappingCount}{50\xspace}",
        r"\newcommand{\RetainedNarrativeWorkCount}{35\xspace}",
        r"\newcommand{\RetainedNarrativeMappingCount}{37\xspace}",
        r"\newcommand{\SourceGroundedWorkCount}{5\xspace}",
        citation_macro("FormulaCorpusCitationsThroughTwentyFive",
                       [row["bibtex_key"] for row in formula_rows if int(row["year"]) <= 2025]),
        citation_macro("FormulaCorpusCitationsTwentySix",
                       [row["bibtex_key"] for row in formula_rows if int(row["year"]) == 2026]),
        citation_macro("TradingCorpusCitationsThroughTwentyFour",
                       [row["bibtex_key"] for row in trading_rows if int(row["year"]) <= 2024]),
        citation_macro("TradingCorpusCitationsTwentyFive",
                       [row["bibtex_key"] for row in trading_rows if int(row["year"]) == 2025]),
        citation_macro("TradingCorpusCitationsTwentySix",
                       [row["bibtex_key"] for row in trading_rows if int(row["year"]) == 2026]),
        citation_macro("ExcludedCorpusCitationsThroughTwentyFour",
                       [row["bibtex_key"] for row in excluded if int(row["year"]) <= 2024]),
        citation_macro("ExcludedCorpusCitationsTwentyFive",
                       [row["bibtex_key"] for row in excluded if int(row["year"]) == 2025]),
        citation_macro("ExcludedCorpusCitationsTwentySix",
                       [row["bibtex_key"] for row in excluded if int(row["year"]) == 2026]),
        "",
    ]
    (root / "docs/paper/generated_corpus_citations.tex").write_text("\n".join(macro_lines), encoding="utf-8")

    mapping = read_csv(root / "paper_runs/submission_evidence/mapping_audit/mapping_audit.csv")
    source_counts: dict[str, int] = {}
    for row in mapping:
        source_counts[row["source_name"]] = source_counts.get(row["source_name"], 0) + 1
    require(set(MAPPING_SOURCE_TO_WORK_ID) <= set(source_counts),
            "retained mapping crosswalk contains a source absent from the mapping ledger")
    mapped_work_ids = set(MAPPING_SOURCE_TO_WORK_ID.values())
    preferred_work_ids = {row["canonical_work_id"] for row in preferred}
    retained_work_ids = {row["canonical_work_id"] for row in retained}
    require(len(mapped_work_ids) == 40 and mapped_work_ids <= retained_work_ids,
            "retained reconstructed-work crosswalk is not 40 works")
    require(sum(source_counts[name] for name in MAPPING_SOURCE_TO_WORK_ID) == 50,
            "retained works do not produce exactly 50 mappings")
    require(len(SOURCE_GROUNDED_WORK_IDS) == 5 and SOURCE_GROUNDED_WORK_IDS <= mapped_work_ids,
            "source-grounded work crosswalk is not five retained works")
    require(len(RETAINED_DIRECT_WORK_IDS) == 8 and RETAINED_DIRECT_WORK_IDS <= mapped_work_ids,
            "retained direct-code crosswalk is not eight reconstructed works")
    require(len(DIAGNOSTIC_DIRECT_WORK_IDS) == 6
            and DIAGNOSTIC_DIRECT_WORK_IDS <= preferred_work_ids - retained_work_ids,
            "diagnostic direct-code crosswalk is not six excluded works")

    preferred_by_system_id = {
        system_id: row["canonical_work_id"]
        for row in preferred
        for system_id in row["system_ids"].split("; ")
        if system_id
    }
    mapping_scope_fields = [
        "source_index",
        "source_name",
        "candidate_id",
        "source_category",
        "mapping_fidelity_tier",
        "screened_system_id",
        "screened_system_name",
        "screen_stratum",
        "screen_main_ft",
        "screen_rationale",
        "canonical_work_id",
        "headline_50_scope",
        "headline_scope_reason",
        "negative_evidence_boundary",
    ]
    mapping_scope_rows = []
    for mapping_row in mapping:
        source_name = mapping_row["source_name"]
        registry_row = registry_row_for_mapping(
            registry, mapping_row["source_index"], source_name
        )
        included = source_name in MAPPING_SOURCE_TO_WORK_ID
        canonical_work_id = (
            MAPPING_SOURCE_TO_WORK_ID[source_name]
            if included
            else preferred_by_system_id.get(
                registry_row["system_id"], "not_applicable_no_scholarly_work"
            )
        )
        if included:
            scope_reason = (
                "included: frozen crosswalk links the mapping to one of the "
                "40 reconstructed works in the 69-work retained F/T corpus"
            )
        else:
            scope_reason = (
                "excluded: screened lineage has main_FT=N; "
                + registry_row["inclusion_exclusion_rationale"]
            )
        mapping_scope_rows.append(
            {
                "source_index": mapping_row["source_index"],
                "source_name": source_name,
                "candidate_id": mapping_row["candidate_id"],
                "source_category": mapping_row["source_category"],
                "mapping_fidelity_tier": mapping_row["mapping_fidelity_tier"],
                "screened_system_id": registry_row["system_id"],
                "screened_system_name": registry_row["system_name"],
                "screen_stratum": registry_row["stratum"],
                "screen_main_ft": registry_row["main_FT"],
                "screen_rationale": registry_row["inclusion_exclusion_rationale"],
                "canonical_work_id": canonical_work_id,
                "headline_50_scope": "included" if included else "excluded",
                "headline_scope_reason": scope_reason,
                "negative_evidence_boundary": mapping_row[
                    "negative_evidence_boundary"
                ],
            }
        )
    included_scope = [
        row for row in mapping_scope_rows if row["headline_50_scope"] == "included"
    ]
    excluded_scope = [
        row for row in mapping_scope_rows if row["headline_50_scope"] == "excluded"
    ]
    require(len(included_scope) == 50 and len(excluded_scope) == 12,
            "mapping-scope ledger is not a 50/12 partition")
    require(len({row["canonical_work_id"] for row in included_scope}) == 40,
            "included mapping-scope rows do not cover 40 works")
    require(all(row["screen_main_ft"] == "Y" for row in included_scope),
            "an included mapping comes from a screened-out lineage")
    require(all(row["screen_main_ft"] == "N" for row in excluded_scope),
            "an excluded diagnostic mapping comes from a retained F/T lineage")
    require(all(row["mapping_fidelity_tier"] == "M0_narrative_translation"
                for row in excluded_scope),
            "excluded diagnostic mappings are not all narrative translations")
    mapping_scope_path = (
        root
        / "paper_runs/submission_evidence/replication_scope/mapping_scope_ledger.csv"
    )
    with mapping_scope_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=mapping_scope_fields, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(mapping_scope_rows)

    sources_by_work: dict[str, list[str]] = {}
    for source_name, work_id in MAPPING_SOURCE_TO_WORK_ID.items():
        sources_by_work.setdefault(work_id, []).append(source_name)
    waterfall_fields = [
        "canonical_work_id", "bibtex_key", "title", "year", "screen_decision",
        "direct_code_route", "native_agent_replication", "code_backed_adaptation",
        "good_faith_reconstruction", "mapping_count", "reconstruction_fidelity",
        "negative_inference_boundary",
    ]
    waterfall_rows = []
    for row in preferred:
        work_id = row["canonical_work_id"]
        mapped_sources = sources_by_work.get(work_id, [])
        mapping_count = sum(source_counts[name] for name in mapped_sources)
        if work_id in RETAINED_DIRECT_WORK_IDS:
            direct_route = "retained_code_attempt"
        elif work_id in DIAGNOSTIC_DIRECT_WORK_IDS:
            direct_route = "diagnostic_code_attempt"
        else:
            direct_route = "not_targeted"
        if work_id in SOURCE_GROUNDED_WORK_IDS:
            fidelity = "source_grounded_component_test"
            boundary = "component_only_not_native_agent_or_full_paper"
        elif work_id in mapped_work_ids:
            fidelity = "narrative_favorable_stress_test"
            boundary = "no_negative_inference_about_source"
        elif row["main_ft"] == "yes":
            fidelity = "availability_only"
            boundary = "no_performance_inference"
        else:
            fidelity = "screened_out"
            boundary = "not_in_retained_performance_corpus"
        waterfall_rows.append({
            "canonical_work_id": work_id,
            "bibtex_key": row["bibtex_key"],
            "title": row["title"],
            "year": row["year"],
            "screen_decision": "retained_formula_or_trading" if row["main_ft"] == "yes" else "screened_out",
            "direct_code_route": direct_route,
            "native_agent_replication": "no",
            "code_backed_adaptation": "yes_released_seed_expression" if work_id == "CensusArxiv260515412" else "no",
            "good_faith_reconstruction": "yes" if work_id in mapped_work_ids else "no",
            "mapping_count": str(mapping_count),
            "reconstruction_fidelity": fidelity,
            "negative_inference_boundary": boundary,
        })
    waterfall = root / "paper_runs/submission_evidence/replication_scope/work_level_evidence_waterfall.csv"
    with waterfall.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=waterfall_fields)
        writer.writeheader()
        writer.writerows(waterfall_rows)

    output = root / "paper_runs/submission_evidence/replication_scope/pretrim_primary_record_inventory.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=metadata[0].keys())
        writer.writeheader()
        writer.writerows(metadata)

    sections = [
        ("Retained formula-discovery works", [row for row in retained if "F" in row["strata"].split("; ")]),
        ("Retained trading works", [row for row in retained if "T" in row["strata"].split("; ")]),
        ("Screened-out benchmark, comparator, and adjacent works", excluded),
    ]
    markdown = [
        "# Complete pre-trim source bibliography",
        "",
        "The screened universe contains **103 system lineages** represented by 105 registry links,",
        "104 distinct URLs, and **98 canonical scholarly works** after duplicate publication",
        "manifestations are collapsed. The retained formula/trading sample contains **67 lineages**",
        "and **69 canonical works**. All 98 screened works are cited in the ICAIF manuscript.",
        "",
    ]
    for heading, group in sections:
        markdown.extend([f"## {heading} ({len(group)})", ""])
        for row in group:
            author = row["authors"].split(";")[0]
            if ";" in row["authors"]:
                author += " et al."
            markdown.append(
                f"- **{author} ({row['year']}). {row['title']}.** "
                f"Systems: {row['system_names']}. [{row['metadata_source']}]({row['primary_url']}) "
                f"(`{row['bibtex_key']}`)."
            )
        markdown.append("")
    (root / "docs/full_corpus_bibliography.md").write_text("\n".join(markdown), encoding="utf-8")

    print({
        "screened_lineages": len(registry),
        "screened_record_links": sum(len([u for u in row["primary_record"].split(" ; ") if u.strip()]) for row in registry),
        "screened_distinct_urls": len(metadata),
        "screened_canonical_works": len(preferred),
        "retained_lineages": sum(row["main_FT"] == "Y" for row in registry),
        "retained_canonical_works": len(retained),
        "formula_works": len(formula_keys),
        "trading_works": len(trading_keys),
        "excluded_works": len(excluded),
        "reconstructed_retained_works": len(mapped_work_ids),
        "retained_mappings": sum(source_counts[name] for name in MAPPING_SOURCE_TO_WORK_ID),
        "availability_only_retained_works": len(retained_work_ids - mapped_work_ids),
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
