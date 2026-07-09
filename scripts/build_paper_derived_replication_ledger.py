#!/usr/bin/env python3
"""Build a paper-derived replication ledger for the alpha_evolve JKP proxy tests.

The ledger ties each candidate proxy back to available paper text or source-table
content, then records the JKP proxy formula and FF5Mom performance result.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
PAPER_TEXT_DIR = BASE / "paper_runs" / "idea_replications" / "paper_text"
PROXY_DIR = BASE / "paper_runs" / "idea_replications" / "jkp_paper_idea_proxies"
OUT_DIR = BASE / "paper_runs" / "idea_replications"
PAPER_LINKS = BASE / "literature_review" / "paper_links.csv"
CODE_LINKS = BASE / "literature_review" / "code_links.csv"
SOURCE_TEXT = BASE / "literature_review" / "source_pasted_text.txt"
CODE_REPO_DIR = BASE / "external_repos_code_links"
REPO_EVIDENCE_CSV = OUT_DIR / "code_link_repo_evidence_summary.csv"
SUMMARY_CSV = PROXY_DIR / "paper_idea_proxy_ff5mom_summary.csv"
META_JSON = PROXY_DIR / "paper_idea_proxy_metadata.json"
COVERAGE_CSV = OUT_DIR / "all_literature_jkp_coverage_summary.csv"

CANDIDATE_LEDGER_CSV = OUT_DIR / "paper_derived_candidate_replication_ledger.csv"
SOURCE_LEDGER_CSV = OUT_DIR / "paper_derived_source_replication_ledger.csv"
LEDGER_REPORT = OUT_DIR / "PAPER_DERIVED_REPLICATION_LEDGER.md"
MAIN_REPORT = BASE / "report.md"

BEAT_FLAG = "beats_ff5mom_positive_alpha_5pct"

EVIDENCE_PATTERNS: dict[str, list[str]] = {
    "factor_mining": [
        r"alpha factor", r"factor mining", r"factor generation", r"formulaic", r"RankIC", r"information coefficient",
    ],
    "sparse_or_cross_sectional_portfolio": [
        r"sparse portfolio", r"top[- ]?m", r"top[- ]?k", r"cross[- ]?section", r"portfolio construction",
    ],
    "agent_trading_workflow": [
        r"multi[- ]?agent", r"trading agent", r"portfolio manager", r"analyst", r"reasoning", r"reflection",
    ],
    "reported_performance_claim": [
        r"Sharpe", r"annualized return", r"CAGR", r"maximum drawdown", r"Sortino", r"Calmar", r"cumulative return",
    ],
    "risk_control": [
        r"risk", r"volatility", r"drawdown", r"CVaR", r"hedg", r"low[- ]?risk", r"downside",
    ],
}

UNAVAILABLE_PATTERNS: dict[str, list[str]] = {
    "news_or_text_signal": [r"news", r"headline", r"sentiment", r"filing", r"earnings call", r"textual"],
    "image_or_multimodal_signal": [r"image", r"chart", r"candlestick", r"multi[- ]?modal", r"visual"],
    "intraday_or_hft_signal": [r"intraday", r"minute", r"high[- ]?frequency", r"candlestick", r"OHLC", r"next candlestick"],
    "live_or_llm_execution": [r"live", r"real[- ]?time", r"LLM", r"prompt", r"agent", r"tool"],
    "non_usa_or_crypto_scope": [r"crypto", r"CSI300", r"CSI500", r"A[- ]?share", r"HSI", r"NASDAQ[- ]?100"],
}

BASIS_PATTERNS: dict[str, list[str]] = {
    "momentum_or_reversal": ["ret_1_0", "ret_3_1", "ret_6_1", "ret_12_1", "ret_18_1", "rmax"],
    "value": ["be_me", "ebit_mev", "ebitda_debt", "sale_me"],
    "quality_or_profitability": ["qmj", "ope_be", "gp_me", "gp_mev", "ni_me", "ocf_me", "at_turnover"],
    "growth_or_investment": ["sale_gr1", "at_gr1"],
    "risk_or_safety": ["rvol", "beta", "betadown", "debt_at", "debt_gr1", "cash_at", "qmj_safety"],
    "liquidity_or_microstructure": ["dolvol", "turnover", "bidaskhl"],
    "issuance_or_accruals": ["oaccruals", "eqnetis"],
}


CANDIDATE_REPO_MAP = {
    "repo_rd_agent_factor_model_compact_ensemble": "microsoft/RD-Agent",
    "code_alphaforge_program_factor": "DulyHao/AlphaForge",
    "code_alphagen_symbolic_factor": "RL-MLDM/alphagen",
}

REF_REPO_MAP = {
    6: ["microsoft/RD-Agent"],
    22: ["DulyHao/AlphaForge", "RL-MLDM/alphagen"],
}

NON_MAPPABLE_NOTES = {
    41: ("not_mappable_crypto_not_usa_equity", "CryptoTrade is crypto-only and outside the USA-equity JKP universe."),
    46: ("not_mappable_benchmark_no_strategy", "QuantCode-Bench evaluates code generation, not a dated alpha strategy."),
    54: ("not_mappable_tooling_no_strategy", "moss-trade-bot-skills is tooling, not a standalone USA-equity alpha strategy."),
    55: ("not_mappable_no_alpha_strategy", "The Alpha Illusion is a critique/reporting protocol paper, not an alpha strategy."),
}


def parse_ref(value: Any) -> int | None:
    if value is None or pd.isna(value):
        return None
    match = re.match(r"\s*(\d+)", str(value))
    return int(match.group(1)) if match else None


def norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def text_for_ref(ref: int) -> tuple[str, str]:
    files = sorted(PAPER_TEXT_DIR.glob(f"{ref:03d}_*.txt"))
    if not files:
        return "", "none"
    try:
        return files[0].read_text(encoding="utf-8", errors="ignore"), str(files[0].relative_to(BASE))
    except OSError:
        return "", "none"


def safe_repo_dir(repo: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "__", str(repo).strip())
    return CODE_REPO_DIR / safe


def load_repo_texts(codes: pd.DataFrame) -> dict[str, str]:
    repo_texts: dict[str, str] = {}
    evidence_rows: list[dict[str, Any]] = []
    for _, row in codes.iterrows():
        repo = str(row.get("repository", "")).strip()
        link_type = str(row.get("link_type", ""))
        if not repo or repo == "nan" or link_type == "supporting_github_source":
            continue
        if repo in repo_texts:
            continue
        dest = safe_repo_dir(repo)
        readme_files: list[Path] = []
        if dest.exists():
            for pattern in ["README*", "readme*", "docs/README*", "docs/readme*"]:
                readme_files.extend(sorted(dest.glob(pattern)))
        parts: list[str] = []
        used_files: list[str] = []
        for f in readme_files[:3]:
            if f.is_file() and f.stat().st_size < 2_000_000:
                try:
                    txt = f.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                parts.append(txt[:12000])
                used_files.append(str(f.relative_to(BASE)))
        text = norm_text("\n".join(parts))
        repo_texts[repo] = text
        evidence_rows.append({
            "repository": repo,
            "repo_dir": str(dest.relative_to(BASE)) if dest.exists() else "",
            "readme_files": ";".join(used_files),
            "readme_text_chars": len(text),
            "evidence_categories": ";".join(matched_categories(text, EVIDENCE_PATTERNS)),
            "unavailable_content": ";".join(matched_categories(text, UNAVAILABLE_PATTERNS)),
        })
    pd.DataFrame(evidence_rows).to_csv(REPO_EVIDENCE_CSV, index=False)
    return repo_texts


def has_repo_evidence_for_ref(ref: int | None, codes: pd.DataFrame, repo_texts: dict[str, str]) -> bool:
    if ref is None:
        return False
    for _, row in codes.iterrows():
        if parse_ref(row.get("source_ref_indices")) == ref:
            repo = str(row.get("repository", "")).strip()
            if repo_texts.get(repo):
                return True
    return False


def source_context_for_ref(ref: int | None, papers: pd.DataFrame, codes: pd.DataFrame, source_text: str, repo_texts: dict[str, str]) -> str:
    chunks: list[str] = []
    if ref is not None:
        pr = papers.loc[papers["ref_index"].eq(ref)]
        if not pr.empty:
            row = pr.iloc[0]
            chunks.append(" ".join(str(row.get(c, "")) for c in ["project_or_paper", "reference_title", "paper_or_project_url"]))
        code_rows = []
        for _, r in codes.iterrows():
            if parse_ref(r.get("source_ref_indices")) == ref:
                repo = str(r.get("repository", "")).strip()
                code_rows.append(" ".join(str(r.get(c, "")) for c in ["project_or_paper", "repository", "notes"]))
                if repo_texts.get(repo):
                    code_rows.append(repo_texts[repo])
        chunks.extend(code_rows)
    if not chunks and source_text:
        chunks.append(source_text[:4000])
    return norm_text(" ".join(chunks))


def matched_categories(text: str, patterns: dict[str, list[str]]) -> list[str]:
    out: list[str] = []
    for category, pats in patterns.items():
        if any(re.search(p, text, flags=re.I) for p in pats):
            out.append(category)
    return out


def short_evidence(text: str, fallback: str) -> str:
    text = norm_text(text)
    if not text:
        return fallback
    priority = [
        r"(alpha mining[^.]{0,220}\.)",
        r"(sparse portfolio[^.]{0,220}\.)",
        r"(factor[^.]{0,220}\.)",
        r"(portfolio[^.]{0,220}\.)",
        r"(Sharpe[^.]{0,220}\.)",
        r"(multi[- ]?agent[^.]{0,220}\.)",
    ]
    for pat in priority:
        m = re.search(pat, text, flags=re.I)
        if m:
            sentence = norm_text(m.group(1))
            return sentence[:360]
    return text[:360]


def replication_basis(formula: str) -> list[str]:
    formula_l = formula.lower()
    out = []
    for category, tokens in BASIS_PATTERNS.items():
        if any(tok.lower() in formula_l for tok in tokens):
            out.append(category)
    return out


def fmt_float(value: Any, digits: int = 3, pct: bool = False) -> str:
    if value is None or pd.isna(value):
        return ""
    val = float(value)
    if pct:
        return f"{val * 100:.2f}%"
    return f"{val:.{digits}f}"


def md_escape(value: Any) -> str:
    s = "" if value is None or pd.isna(value) else str(value)
    return s.replace("|", "\\|").replace("\n", " ")


def md_table(df: pd.DataFrame, cols: list[str], headers: list[str] | None = None) -> str:
    headers = headers or cols
    lines = ["| " + " | ".join(md_escape(h) for h in headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(md_escape(row.get(c, "")) for c in cols) + " |")
    return "\n".join(lines)


def main() -> None:
    papers = pd.read_csv(PAPER_LINKS)
    codes = pd.read_csv(CODE_LINKS)
    summary = pd.read_csv(SUMMARY_CSV)
    metadata = json.loads(META_JSON.read_text(encoding="utf-8"))
    definitions: dict[str, dict[str, Any]] = metadata["candidate_definitions"]
    source_text = SOURCE_TEXT.read_text(encoding="utf-8", errors="ignore") if SOURCE_TEXT.exists() else ""
    repo_texts = load_repo_texts(codes)

    rows: list[dict[str, Any]] = []
    for _, result in summary.iterrows():
        cid = result["candidate_id"]
        definition = definitions.get(cid, {})
        ref = parse_ref(result.get("paper_ref") or definition.get("paper_ref"))
        paper_text, paper_text_path = text_for_ref(ref) if ref is not None else ("", "none")
        context = paper_text if paper_text else source_context_for_ref(ref, papers, codes, source_text, repo_texts)
        if not paper_text:
            for mapped_repo in REF_REPO_MAP.get(ref, []):
                if repo_texts.get(mapped_repo):
                    context = norm_text(context + " " + repo_texts[mapped_repo])
        candidate_repo = CANDIDATE_REPO_MAP.get(str(cid))
        if (not paper_text) and candidate_repo and repo_texts.get(candidate_repo):
            context = norm_text(context + " " + repo_texts[candidate_repo])
        repo_evidence_available = has_repo_evidence_for_ref(ref, codes, repo_texts) or bool(candidate_repo and repo_texts.get(candidate_repo))
        source_basis = "paper_text" if paper_text else ("repo_readme_or_source_notes" if repo_evidence_available else "source_table_or_repo_notes")
        if ref in (6, 13, 14):
            source_basis = "repo_readme_missing_extracted_paper_text" if repo_evidence_available else "source_table_or_repo_notes_missing_extracted_paper_text"
        categories = matched_categories(context, EVIDENCE_PATTERNS)
        unavailable = matched_categories(context, UNAVAILABLE_PATTERNS)
        formula = str(definition.get("proxy_formula", result.get("proxy_formula", "")))
        basis = replication_basis(formula)
        evidence = short_evidence(context, str(definition.get("paper_idea", result.get("paper_idea", ""))))
        rows.append({
            "candidate_id": cid,
            "ref_index": ref if ref is not None else "",
            "paper_ref": definition.get("paper_ref", result.get("paper_ref", "")),
            "source_basis": source_basis,
            "paper_text_path": paper_text_path,
            "paper_idea": definition.get("paper_idea", result.get("paper_idea", "")),
            "paper_evidence_summary": evidence,
            "evidence_categories": ";".join(categories),
            "unavailable_paper_content_not_replicated": ";".join(unavailable),
            "jkp_replication_basis": ";".join(basis),
            "proxy_formula": formula,
            "strategy": definition.get("strategy", result.get("strategy", "")),
            "replication_scope": definition.get("replication_scope", "paper_or_code_in_spirit_proxy"),
            "candidate_standalone_oos_sharpe": result.get("candidate_standalone_oos_sharpe"),
            "alpha_annualized": result.get("alpha_annualized"),
            "alpha_tstat_hac": result.get("alpha_tstat_hac"),
            "information_ratio": result.get("information_ratio"),
            "appraisal_ratio": result.get("appraisal_ratio"),
            "grs_f": result.get("grs_f"),
            "grs_p_value": result.get("grs_p_value"),
            "combined_minus_old_sharpe": result.get("combined_minus_old_sharpe"),
            "beats_ff5mom_positive_alpha_5pct": bool(result.get(BEAT_FLAG)),
        })

    candidate_ledger = pd.DataFrame(rows).sort_values(["ref_index", "candidate_id"], na_position="last")
    candidate_ledger.to_csv(CANDIDATE_LEDGER_CSV, index=False)

    source_refs = set(int(x) for x in papers["ref_index"].dropna().tolist())
    for x in codes["source_ref_indices"].dropna().tolist():
        ref = parse_ref(x)
        if ref is not None:
            source_refs.add(ref)

    source_rows: list[dict[str, Any]] = []
    for ref in sorted(source_refs):
        cand = candidate_ledger.loc[candidate_ledger["ref_index"].eq(ref)].copy()
        paper_text, paper_text_path = text_for_ref(ref)
        paper_row = papers.loc[papers["ref_index"].eq(ref)]
        title = ""
        if not paper_row.empty:
            title = str(paper_row.iloc[0].get("project_or_paper") or paper_row.iloc[0].get("reference_title") or "")
        code_repos = sorted({str(r.get("repository")) for _, r in codes.iterrows() if parse_ref(r.get("source_ref_indices")) == ref and pd.notna(r.get("repository"))})
        code_repos = sorted(set(code_repos).union(REF_REPO_MAP.get(ref, [])))
        if not title and code_repos:
            title = ", ".join(code_repos)
        context = paper_text if paper_text else source_context_for_ref(ref, papers, codes, source_text, repo_texts)
        status = "jkp_proxy_tested" if not cand.empty else NON_MAPPABLE_NOTES.get(ref, ("not_mapped", ""))[0]
        note = ""
        if ref in NON_MAPPABLE_NOTES:
            note = NON_MAPPABLE_NOTES[ref][1]
        elif cand.empty:
            note = "No candidate was mapped; review required."
        else:
            note = "Paper/source idea translated into at least one explicit JKP-USA proxy and evaluated vs FF5Mom."
        best = None
        if not cand.empty:
            best = cand.sort_values(["combined_minus_old_sharpe", "alpha_tstat_hac"], ascending=[False, False]).iloc[0]
        source_rows.append({
            "ref_index": ref,
            "title_or_source": title,
            "code_repositories": ";".join(code_repos),
            "source_status": status,
            "candidate_count": int(len(cand)),
            "candidate_ids": ";".join(cand["candidate_id"].astype(str).tolist()),
            "paper_text_available": bool(paper_text),
            "repo_readme_available": has_repo_evidence_for_ref(ref, codes, repo_texts) or any(bool(repo_texts.get(rp)) for rp in REF_REPO_MAP.get(ref, [])),
            "paper_text_path": paper_text_path if paper_text else "",
            "evidence_categories": ";".join(matched_categories(context, EVIDENCE_PATTERNS)),
            "unavailable_paper_content_not_replicated": ";".join(matched_categories(context, UNAVAILABLE_PATTERNS)),
            "best_candidate_id": "" if best is None else best["candidate_id"],
            "best_sharpe": None if best is None else best["candidate_standalone_oos_sharpe"],
            "best_alpha_annualized": None if best is None else best["alpha_annualized"],
            "best_alpha_tstat_hac": None if best is None else best["alpha_tstat_hac"],
            "best_information_ratio": None if best is None else best["information_ratio"],
            "best_grs_f": None if best is None else best["grs_f"],
            "best_grs_p_value": None if best is None else best["grs_p_value"],
            "best_span_lift": None if best is None else best["combined_minus_old_sharpe"],
            "best_beats_ff5mom": False if best is None else bool(best["beats_ff5mom_positive_alpha_5pct"]),
            "note": note,
        })
    source_ledger = pd.DataFrame(source_rows)
    source_ledger.to_csv(SOURCE_LEDGER_CSV, index=False)

    n_candidate = len(candidate_ledger)
    n_sources = len(source_ledger)
    n_tested_sources = int(source_ledger["source_status"].eq("jkp_proxy_tested").sum())
    n_text_sources = int(source_ledger["paper_text_available"].sum())
    n_beat = int(candidate_ledger["beats_ff5mom_positive_alpha_5pct"].sum())
    n_paper_text_candidates = int(candidate_ledger["source_basis"].eq("paper_text").sum())
    n_repo_readme_candidates = int(candidate_ledger["source_basis"].astype(str).str.contains("repo_readme").sum())
    n_text_or_repo_candidates = n_paper_text_candidates + n_repo_readme_candidates

    beaters = candidate_ledger.loc[candidate_ledger["beats_ff5mom_positive_alpha_5pct"]].copy()
    beaters = beaters.sort_values("combined_minus_old_sharpe", ascending=False)
    for col in ["candidate_standalone_oos_sharpe", "alpha_tstat_hac", "information_ratio", "appraisal_ratio", "grs_f", "grs_p_value", "combined_minus_old_sharpe"]:
        beaters[col + "_fmt"] = beaters[col].map(lambda x: fmt_float(x, 4 if col == "grs_p_value" else 3))
    beaters["alpha_annualized_fmt"] = beaters["alpha_annualized"].map(lambda x: fmt_float(x, pct=True))

    source_view = source_ledger.copy()
    for col in ["best_sharpe", "best_alpha_tstat_hac", "best_information_ratio", "best_grs_f", "best_grs_p_value", "best_span_lift"]:
        source_view[col + "_fmt"] = source_view[col].map(lambda x: fmt_float(x, 4 if col == "best_grs_p_value" else 3))
    source_view["best_alpha_annualized_fmt"] = source_view["best_alpha_annualized"].map(lambda x: fmt_float(x, pct=True))

    report: list[str] = []
    report.append("# Paper-Derived JKP Replication Ledger")
    report.append("")
    report.append("This ledger answers the question: what valuable trading content could be gathered from each paper/source, and what was actually reproduced on the approved JKP USA universe?")
    report.append("")
    report.append("Inputs remain restricted to the approved read-only JKP/return-pipeline data for returns. Paper text is used only to choose and document in-spirit proxies; no paper-shipped returns, China/A-share data, yfinance data, or external return streams are used for the performance metrics.")
    report.append("")
    report.append("## Coverage")
    report.append("")
    report.append(f"- Unique source refs in paper/code tables: {n_sources}")
    report.append(f"- Source refs with extracted paper text available: {n_text_sources}")
    report.append(f"- Source refs translated into at least one JKP-USA proxy: {n_tested_sources}")
    report.append(f"- Candidate proxies backtested and evaluated vs FF5Mom: {n_candidate}")
    report.append(f"- Candidate proxies backed by extracted paper text: {n_paper_text_candidates}")
    report.append(f"- Candidate proxies backed by cloned-repo README/source evidence because paper text was not available or not applicable: {n_repo_readme_candidates}")
    report.append(f"- Candidate proxies backed by either extracted paper text or cloned repo evidence: {n_text_or_repo_candidates}")
    report.append(f"- Strict FF5Mom beaters: {n_beat}")
    report.append("")
    report.append("Missing extracted paper text remains for refs 6, 13, and 14. Ref 13's arXiv PDF URL returned HTML during recovery, and refs 6/14 are hosted behind pages that did not provide an automated paper text in the current workspace. Their proxies are therefore marked as source-table/repo-notes based, not paper-text based.")
    report.append("")
    report.append("## Best Positive FF5Mom Results")
    report.append("")
    report.append(md_table(
        beaters,
        ["candidate_id", "paper_ref", "source_basis", "jkp_replication_basis", "candidate_standalone_oos_sharpe_fmt", "alpha_annualized_fmt", "alpha_tstat_hac_fmt", "information_ratio_fmt", "grs_p_value_fmt", "combined_minus_old_sharpe_fmt"],
        ["candidate", "source", "evidence", "JKP basis", "Sharpe", "alpha ann.", "alpha t", "IR", "GRS p", "span lift"],
    ))
    report.append("")
    report.append("## Source-Level Ledger")
    report.append("")
    report.append(md_table(
        source_view,
        ["ref_index", "title_or_source", "source_status", "candidate_count", "evidence_categories", "unavailable_paper_content_not_replicated", "best_candidate_id", "best_sharpe_fmt", "best_alpha_annualized_fmt", "best_alpha_tstat_hac_fmt", "best_information_ratio_fmt", "best_grs_p_value_fmt", "best_beats_ff5mom", "note"],
        ["ref", "paper/source", "status", "n", "paper content gathered", "not replicated", "best candidate", "Sharpe", "alpha ann.", "alpha t", "IR", "GRS p", "beats", "note"],
    ))
    report.append("")
    report.append("## Candidate-Level Ledger")
    report.append("")
    cand_view = candidate_ledger.copy()
    for col in ["candidate_standalone_oos_sharpe", "alpha_tstat_hac", "information_ratio", "grs_f", "grs_p_value", "combined_minus_old_sharpe"]:
        cand_view[col + "_fmt"] = cand_view[col].map(lambda x: fmt_float(x, 4 if col == "grs_p_value" else 3))
    cand_view["alpha_annualized_fmt"] = cand_view["alpha_annualized"].map(lambda x: fmt_float(x, pct=True))
    report.append(md_table(
        cand_view,
        ["candidate_id", "paper_ref", "source_basis", "evidence_categories", "unavailable_paper_content_not_replicated", "jkp_replication_basis", "proxy_formula", "strategy", "candidate_standalone_oos_sharpe_fmt", "alpha_annualized_fmt", "alpha_tstat_hac_fmt", "information_ratio_fmt", "grs_p_value_fmt", "combined_minus_old_sharpe_fmt", "beats_ff5mom_positive_alpha_5pct"],
        ["candidate", "source", "evidence", "paper content gathered", "not replicated", "JKP basis", "proxy formula", "strategy", "Sharpe", "alpha ann.", "alpha t", "IR", "GRS p", "span lift", "beats"],
    ))
    report.append("")
    LEDGER_REPORT.write_text("\n".join(report), encoding="utf-8")

    section = []
    section.append("<!-- PAPER_DERIVED_REPLICATION_LEDGER_START -->")
    section.append("")
    section.append("## Paper-derived replication ledger")
    section.append("")
    section.append("I added a paper-derived ledger that makes the in-spirit replication path explicit. For each source reference, it records whether extracted paper text was available, what content was gathered from that text or from source/repo notes, what could not be reproduced on JKP because it requires news/images/intraday/live/crypto inputs, the JKP proxy formula used, and the FF5Mom result.")
    section.append("")
    section.append(f"- Source refs translated into JKP-USA proxies: {n_tested_sources} / {n_sources}")
    section.append(f"- Candidate proxies backtested/evaluated: {n_candidate}")
    section.append(f"- Candidates with extracted paper-text evidence: {n_paper_text_candidates} / {n_candidate}")
    section.append(f"- Additional candidates with cloned-repo README/source evidence: {n_repo_readme_candidates} / {n_candidate}")
    section.append(f"- Candidates backed by paper text or repo evidence: {n_text_or_repo_candidates} / {n_candidate}")
    section.append(f"- Strict FF5Mom beaters: {n_beat} / {n_candidate}")
    section.append("- Remaining non-mappable refs are not alpha strategies on the approved USA-equity universe: CryptoTrade, QuantCode-Bench, moss-trade-bot-skills, and The Alpha Illusion critique.")
    section.append("")
    section.append("Files:")
    section.append("")
    section.append(f"- `{LEDGER_REPORT.relative_to(BASE)}`")
    section.append(f"- `{CANDIDATE_LEDGER_CSV.relative_to(BASE)}`")
    section.append(f"- `{SOURCE_LEDGER_CSV.relative_to(BASE)}`")
    section.append("")
    section.append("<!-- PAPER_DERIVED_REPLICATION_LEDGER_END -->")
    section_text = "\n".join(section)
    old = MAIN_REPORT.read_text(encoding="utf-8")
    start = "<!-- PAPER_DERIVED_REPLICATION_LEDGER_START -->"
    end = "<!-- PAPER_DERIVED_REPLICATION_LEDGER_END -->"
    if start in old and end in old:
        old = old.split(start)[0].rstrip() + "\n\n" + section_text + "\n\n" + old.split(end, 1)[1].lstrip()
    else:
        insert_after = "## Return-Data Scope"
        if insert_after in old:
            idx = old.index(insert_after)
            old = old[:idx].rstrip() + "\n\n" + section_text + "\n\n" + old[idx:]
        else:
            old = old.rstrip() + "\n\n" + section_text + "\n"
    MAIN_REPORT.write_text(old, encoding="utf-8")

    print(json.dumps({
        "candidate_ledger_csv": str(CANDIDATE_LEDGER_CSV.relative_to(BASE)),
        "source_ledger_csv": str(SOURCE_LEDGER_CSV.relative_to(BASE)),
        "repo_evidence_csv": str(REPO_EVIDENCE_CSV.relative_to(BASE)),
        "ledger_report": str(LEDGER_REPORT.relative_to(BASE)),
        "source_refs": n_sources,
        "tested_sources": n_tested_sources,
        "candidate_proxies": n_candidate,
        "paper_text_candidates": n_paper_text_candidates,
        "repo_readme_candidates": n_repo_readme_candidates,
        "paper_or_repo_evidence_candidates": n_text_or_repo_candidates,
        "ff5mom_beaters": n_beat,
    }, indent=2))


if __name__ == "__main__":
    main()
