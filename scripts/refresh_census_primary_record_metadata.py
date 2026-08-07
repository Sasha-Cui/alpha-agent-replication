#!/usr/bin/env python3
from __future__ import annotations

import csv
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "literature_review/census_v1/system_registry.csv"
OUTPUT = ROOT / "literature_review/census_v1/primary_record_metadata.csv"
USER_AGENT = "alpha-evidence-citation-audit/1.0 (research metadata validation)"
ATOM = "{http://www.w3.org/2005/Atom}"


MANUAL = {
    "https://openreview.net/forum?id=lNmZrawUMu": {
        "title": "AlphaAgentEvo: Evolution-Oriented Alpha Mining via Self-Evolving Agentic Reinforcement Learning",
        "authors": "Ziyi Tang; Xuexiong Yin; Weixing Chen; Zechuan Chen; Yongsen Zheng; Wenxuan Ye; Keze Wang; Liang Lin",
        "year": "2026",
        "venue": "International Conference on Learning Representations",
        "entry_type": "inproceedings",
        "metadata_source": "OpenReview primary record and ICLR publication record",
    },
    "https://openreview.net/forum?id=ziuTkKhgT0": {
        "title": "RAPTOR: Reasoned Agentic Portfolio Trading with Orchestrated Rebalancing",
        "authors": "Blake Almon; Matthew Caliboso; Alex Kim; Rohan Dutta; Rohan Raman; Mithil Srungarapu; Vasu Sharma; Kevin Zhu",
        "year": "2025",
        "venue": "NeurIPS 2025 Workshop on New Opportunities for Research and Applications in Finance",
        "entry_type": "inproceedings",
        "metadata_source": "OpenReview primary record",
    },
    "https://alphabench.cc/": {
        "title": "AlphaBench: Benchmarking Large Language Models in Formulaic Alpha Factor Mining",
        "authors": "Haochen Luo; Ho Tin Ko; Jiandong Chen; David Sun; Yuan Zhang; Chen Liu",
        "year": "2026",
        "venue": "The Fourteenth International Conference on Learning Representations",
        "entry_type": "inproceedings",
        "metadata_source": "official AlphaBench citation block",
    },
    "https://doi.org/10.1145/3774904.3792821": {
        "title": "When Agents Trade: Live Multi-Market Trading Arena for LLM Agents",
        "authors": "Lingfei Qian; Xueqing Peng; Yan Wang; Vincent Jim Zhang; Huan He; Hanley Smith; Yi Han; Yueru He; Haohang Li; Yupeng Cao; Yangyang Yu; Alejandro Lopez-Lira; Peng Lu; Jian-Yun Nie; Guojun Xiong; Jimin Huang; Sophia Ananiadou",
        "year": "2026",
        "venue": "Proceedings of the ACM Web Conference 2026",
        "entry_type": "inproceedings",
        "metadata_source": "official project publication record",
    },
    "https://www.set-science.com/manage/uploads/ICOF2025_00101/SETSCI_ICOF2025_00101_002.pdf": {
        "title": "AICrypto-Assistant: A Multi-Agent LLM Platform for Democratizing Crypto-Asset Analysis",
        "authors": "Mimoza Dimodugno; Mehdi Mammadov",
        "year": "2025",
        "venue": "International Conference on Open Finance",
        "entry_type": "inproceedings",
        "metadata_source": "publisher-hosted conference paper",
    },
}


MANIFESTATION_GROUPS = {
    "https://arxiv.org/abs/2308.00016": ("WorkAlphaGPT", "no"),
    "https://aclanthology.org/2025.emnlp-demos.14/": ("WorkAlphaGPT", "yes"),
    "https://arxiv.org/abs/2409.06289": ("WorkAutomateStrategy", "no"),
    "https://aclanthology.org/2025.findings-emnlp.1005/": ("WorkAutomateStrategy", "yes"),
    "https://arxiv.org/abs/2510.11695": ("WorkAgentMarketArena", "no"),
    "https://doi.org/10.1145/3774904.3792821": ("WorkAgentMarketArena", "yes"),
    "https://arxiv.org/abs/2505.07078": ("WorkFINSABER", "no"),
    "https://doi.org/10.1145/3770854.3785702": ("WorkFINSABER", "yes"),
    "https://arxiv.org/abs/2412.18174": ("WorkInvestorBench", "no"),
    "https://aclanthology.org/2025.acl-long.126/": ("WorkInvestorBench", "yes"),
    "https://www.set-science.com/manage/uploads/ICOF2025_00101/SETSCI_ICOF2025_00101_002.pdf": ("WorkAICryptoAssistant", "no"),
    "https://doi.org/10.36287/setsci.24.2.017": ("WorkAICryptoAssistant", "yes"),
}


class CitationMetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.values: dict[str, list[str]] = {}

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "meta":
            return
        item = {key.lower(): value for key, value in attrs}
        name = item.get("name", "").lower()
        content = item.get("content", "")
        if name.startswith("citation_") and content:
            self.values.setdefault(name, []).append(html.unescape(content))


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except Exception as exc:  # network retry is intentionally broad
            last = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"failed to fetch {url}: {last}")


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def arxiv_id(url: str) -> str | None:
    match = re.search(r"(?:abs|html|pdf)/(\d{4}\.\d{4,6})(?:v\d+)?", url)
    return match.group(1) if match else None


def arxiv_records(ids: list[str]) -> dict[str, dict[str, str]]:
    output: dict[str, dict[str, str]] = {}
    for start in range(0, len(ids), 20):
        batch = ids[start:start + 20]
        query = urllib.parse.urlencode({"id_list": ",".join(batch), "max_results": len(batch)})
        root = ET.fromstring(fetch(f"https://export.arxiv.org/api/query?{query}"))
        for entry in root.findall(f"{ATOM}entry"):
            identifier = arxiv_id(entry.findtext(f"{ATOM}id", ""))
            if not identifier:
                continue
            authors = [clean(node.findtext(f"{ATOM}name", "")) for node in entry.findall(f"{ATOM}author")]
            published = entry.findtext(f"{ATOM}published", "")
            primary = entry.find("{http://arxiv.org/schemas/atom}primary_category")
            output[identifier] = {
                "title": clean(entry.findtext(f"{ATOM}title", "")),
                "authors": "; ".join(authors),
                "year": published[:4],
                "venue": "arXiv",
                "entry_type": "misc",
                "source_identifier": identifier,
                "primary_class": primary.attrib.get("term", "") if primary is not None else "",
                "metadata_source": "arXiv API",
            }
        time.sleep(3)
    return output


def acl_record(url: str) -> dict[str, str]:
    parser = CitationMetaParser()
    parser.feed(fetch(url).decode("utf-8", errors="replace"))
    values = parser.values
    date = (values.get("citation_publication_date") or values.get("citation_date") or [""])[0]
    venue = (values.get("citation_conference_title") or values.get("citation_journal_title") or ["ACL Anthology"])[0]
    identifier = urllib.parse.urlparse(url).path.strip("/")
    return {
        "title": clean((values.get("citation_title") or [""])[0]),
        "authors": "; ".join(clean(v) for v in values.get("citation_author", [])),
        "year": re.search(r"(?:19|20)\d{2}", date).group(0) if re.search(r"(?:19|20)\d{2}", date) else identifier[:4],
        "venue": clean(venue),
        "entry_type": "inproceedings",
        "source_identifier": identifier,
        "primary_class": "",
        "metadata_source": "ACL Anthology citation metadata",
    }


def doi_record(url: str) -> dict[str, str]:
    doi = url.split("doi.org/", 1)[1].rstrip("/")
    payload = json.loads(fetch(f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='/')}").decode("utf-8"))["message"]
    authors = []
    for author in payload.get("author", []):
        authors.append(clean(" ".join(x for x in [author.get("given", ""), author.get("family", "")] if x)))
    dates = payload.get("published-print") or payload.get("published-online") or payload.get("issued") or {}
    parts = dates.get("date-parts", [[""]])
    venue = (payload.get("container-title") or ["Published work"])[0]
    entry_type = "inproceedings" if payload.get("type") in {"proceedings-article", "proceedings"} else "article"
    return {
        "title": clean((payload.get("title") or [""])[0]),
        "authors": "; ".join(authors),
        "year": str(parts[0][0]),
        "venue": clean(venue),
        "entry_type": entry_type,
        "source_identifier": doi,
        "primary_class": "",
        "metadata_source": "Crossref API",
    }


def bibtex_key(url: str) -> str:
    if url == "https://aka.ms/RD-Agent-Tech-Report":
        return "CensusArxiv250514738"
    if identifier := arxiv_id(url):
        return "CensusArxiv" + identifier.replace(".", "")
    parsed = urllib.parse.urlparse(url)
    if "aclanthology.org" in parsed.netloc:
        return "CensusACL" + re.sub(r"[^A-Za-z0-9]", "", parsed.path)
    if "doi.org" in parsed.netloc:
        return "CensusDOI" + re.sub(r"[^A-Za-z0-9]", "", url.split("doi.org/", 1)[1])
    if "openreview.net" in parsed.netloc:
        return "CensusOR" + urllib.parse.parse_qs(parsed.query)["id"][0]
    return "CensusWeb" + re.sub(r"[^A-Za-z0-9]", "", parsed.netloc + parsed.path)[-48:]


def main() -> None:
    with REGISTRY.open(newline="", encoding="utf-8") as stream:
        registry = list(csv.DictReader(stream, delimiter="|"))
    by_url: dict[str, list[dict[str, str]]] = {}
    for row in registry:
        for url in (part.strip() for part in row["primary_record"].split(" ; ")):
            if url:
                by_url.setdefault(url, []).append(row)
    ids = sorted({identifier for url in by_url if (identifier := arxiv_id(url))})
    ids.append("2505.14738")  # aka.ms/RD-Agent-Tech-Report resolves to this arXiv record.
    arxiv = arxiv_records(sorted(set(ids)))
    output = []
    for url, systems in sorted(by_url.items()):
        if url in MANUAL:
            metadata = dict(MANUAL[url])
            metadata.setdefault("source_identifier", urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("id", [url])[0])
            metadata.setdefault("primary_class", "")
        elif identifier := arxiv_id(url):
            metadata = dict(arxiv[identifier])
        elif url == "https://aka.ms/RD-Agent-Tech-Report":
            metadata = dict(arxiv["2505.14738"])
            metadata["metadata_source"] = "arXiv API via resolved aka.ms primary record"
        elif "aclanthology.org" in url:
            metadata = acl_record(url)
        elif "doi.org" in url:
            metadata = doi_record(url)
        else:
            metadata = {
                "title": systems[0]["system_name"],
                "authors": "",
                "year": "",
                "venue": "",
                "entry_type": "misc",
                "source_identifier": url,
                "primary_class": "",
                "metadata_source": "UNRESOLVED",
            }
        work_id, preferred = MANIFESTATION_GROUPS.get(url, (bibtex_key(url), "yes"))
        output.append({
            "bibtex_key": bibtex_key(url),
            "canonical_work_id": work_id,
            "preferred_citation": preferred,
            "primary_url": url,
            **metadata,
            "system_ids": "; ".join(sorted({r["system_id"] for r in systems})),
            "system_names": "; ".join(sorted({r["system_name"] for r in systems})),
            "strata": "; ".join(sorted({r["stratum"] for r in systems})),
            "main_ft": "yes" if any(r["main_FT"] == "Y" for r in systems) else "no",
            "inclusion_exclusion_rationale": " || ".join(sorted({r["inclusion_exclusion_rationale"] for r in systems})),
        })
    fieldnames = [
        "bibtex_key", "canonical_work_id", "preferred_citation", "primary_url", "title", "authors", "year", "venue", "entry_type",
        "source_identifier", "primary_class", "metadata_source", "system_ids", "system_names",
        "strata", "main_ft", "inclusion_exclusion_rationale",
    ]
    with OUTPUT.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output)
    unresolved = [row for row in output if row["metadata_source"] == "UNRESOLVED"]
    print({
        "record_links": len(output),
        "canonical_works": len({r["canonical_work_id"] for r in output}),
        "main_ft_record_links": sum(r["main_ft"] == "yes" for r in output),
        "main_ft_canonical_works": len({r["canonical_work_id"] for r in output if r["main_ft"] == "yes"}),
        "unresolved": len(unresolved),
    })
    for row in unresolved:
        print("UNRESOLVED", row["primary_url"], row["system_names"])


if __name__ == "__main__":
    main()
