#!/usr/bin/env python3
"""Collect and combine bibliographic records for the secure code review survey."""
import argparse
import html
import json
from pathlib import Path
import re
import time
from urllib.parse import quote, unquote
import xml.etree.ElementTree as ET

import pandas as pd
import requests


# Platform configuration
PLATFORMS = {
    # Google Scholar: file import
    "google": {},
    # IEEE Xplore: Metadata API
    "ieee": {"api_url": "", "api_key": ""},
    # Elsevier Scopus
    "scopus": {"api_url": "", "api_key": "", "inst_token": ""},  # Optional institution token
    # ACM publications via Crossref
    "acm": {"api_url": "", "member_id": "320"},
    # DBLP
    "dblp": {"api_url": "", "bibtex_url": ""},
    # arXiv: public Atom API
    "arxiv": {"api_url": ""},
    # Springer Nature Metadata API
    "springer": {"api_url": "", "api_key": "", "bibtex_url": ""},
}
# DOI content negotiation / Crossref BibTeX endpoint; use a {doi} placeholder.
DOI_BIBTEX_URL = ""
PAGE_SIZE = 25
REQUEST_INTERVAL = 1

CODE_REVIEW_TERMS = [
    "Code review", "Review comment", "Code change", "Modern code review",
    "Peer code review", "Code review process", "Code analysis", "Code inspection",
    "Code review practice", "Reviewing code", "Code review comment", "Code reviewer",
]

SECURITY_TERMS = [
    "Security issue", "Security defect", "Security vulnerabilities",
    "Vulnerability detection", "Software security", "Security checklist",
    "Vulnerable function", "Issue identification", "Software vulnerabilities",
    "Software vulnerability", "Security knowledge", "Security expert", "CWE",
    "Common Weakness Enumeration", "Detect vulnerabilities", "Vulnerability type",
    "Identified security", "Potential security", "Application security",
    "Vulnerable code", "Issue categories", "Exploitable vulnerability",
    "Ensure security", "Vulnerable code change", "Pointer dereference",
    "Code security", "Security assessment", "Secure code", "Security concern",
    "Issue detect", "Security review", "Issue location", "Issue repair",
]

FIELDS = ["platform", "title", "doi", "year", "authors", "venue", "type",
          "url", "abstract", "bibtex", "language", "query", "source_file"]

ALIASES = {
    "title": ["title", "document title", "article title"],
    "doi": ["doi", "document doi"],
    "url": ["url", "link", "article url", "pdf link"],
    "year": ["year", "publication year", "bibtex_year"],
    "authors": ["authors", "author"],
    "venue": ["venue", "journal", "publication title", "source title"],
    "type": ["type", "document type", "publication type", "bibtex_type"],
    "abstract": ["abstract", "summary"],
    "bibtex": ["bibtex", "bibtex entry"],
    "language": ["language"],
    "query": ["query", "keyword", "keywords"],
}


def normalize_doi(value):
    match = re.search(r'10\.\d{4,9}/[^\s"<>]+', unquote(str(value)), re.I)
    return match.group().casefold() if match else ""


def normalize_record(row, platform, source=""):
    row = {str(key).strip().casefold(): str(value).strip()
           for key, value in row.items() if value is not None}
    record = dict.fromkeys(FIELDS, "")
    for field, aliases in ALIASES.items():
        record[field] = next((row[name] for name in aliases if row.get(name)), "")
    record["title"] = html.unescape(record["title"])
    record["doi"] = normalize_doi(record["doi"]) or normalize_doi(record["url"])
    record["platform"] = platform
    record["source_file"] = source
    return record


def import_records(paths, platform, encoding="utf-8-sig", columns=None):
    records = []
    for path in paths:
        if path.suffix.lower() == ".json":
            rows = json.loads(path.read_text(encoding="utf-8"))
        elif path.suffix.lower() == ".xlsx":
            sheets = pd.read_excel(path, sheet_name=None, dtype=str,
                                   header=None if columns else 0, names=columns)
            rows = pd.concat(sheets.values(), ignore_index=True).fillna("").to_dict("records")
        else:
            rows = pd.read_csv(path, encoding=encoding, dtype=str,
                               header=None if columns else 0, names=columns).fillna("").to_dict("records")
        records.extend(normalize_record(row, platform, path.name) for row in rows)
    return [row for row in records if row["title"] and row["title"].casefold() not in ("title", "get access")]


def queries(platform):
    for review in CODE_REVIEW_TERMS:
        for security in SECURITY_TERMS:
            if platform == "scopus":
                yield f'TITLE-ABS-KEY("{review}") AND TITLE-ABS-KEY("{security}")'
            elif platform == "dblp":
                yield f'"{review.upper()}" "{security.upper()}"'
            elif platform == "arxiv":
                yield f'(ti:"{review}" OR abs:"{review}") AND (ti:"{security}" OR abs:"{security}")'
            else:
                yield f'"{review}" AND "{security}"'


def get(url, params=None, headers=None, interval=REQUEST_INTERVAL):
    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    time.sleep(interval)
    return response


# IEEE Xplore

def search_ieee(query, config):
    start = 1
    while True:
        data = get(config["api_url"], {
            "apikey": config["api_key"], "format": "json", "querytext": query,
            "start_record": start, "max_records": PAGE_SIZE,
        }).json()
        total = int(data["total_records"])
        articles = data.get("articles", [])
        for article in articles:
            authors = article.get("authors", {}).get("authors", [])
            yield {
                "title": article["title"], "doi": article.get("doi", ""),
                "year": article.get("publication_year", ""),
                "authors": "; ".join(author.get("full_name", "") for author in authors),
                "venue": article.get("publication_title", ""),
                "type": article.get("content_type", ""),
                "abstract": article.get("abstract", ""),
                "url": article.get("abstract_url", "") or article.get("html_url", ""),
            }
        start += len(articles)
        if start > total:
            break
        if not articles:
            raise RuntimeError("Incomplete IEEE page")


# arXiv

def search_arxiv(query, config):
    ns = {"atom": "http://www.w3.org/2005/Atom",
          "open": "http://a9.com/-/spec/opensearch/1.1/",
          "arxiv": "http://arxiv.org/schemas/atom"}
    start = 0
    while True:
        response = get(config["api_url"], {
            "search_query": query, "start": start, "max_results": PAGE_SIZE,
            "sortBy": "relevance", "sortOrder": "descending",
        }, interval=3)
        feed = ET.fromstring(response.content)
        entries = feed.findall("atom:entry", ns)
        for entry in entries:
            def content(name):
                return " ".join(entry.findtext(name, default="", namespaces=ns).split())
            if content("atom:title").casefold() == "error":
                raise RuntimeError(content("atom:summary"))
            yield {
                "title": content("atom:title"), "doi": content("arxiv:doi"),
                "year": content("atom:published")[:4],
                "authors": "; ".join(a.findtext("atom:name", default="", namespaces=ns)
                                     for a in entry.findall("atom:author", ns)),
                "venue": content("arxiv:journal_ref") or "arXiv",
                "type": "preprint", "abstract": content("atom:summary"),
                "url": content("atom:id"),
            }
        total = int(feed.findtext("open:totalResults", namespaces=ns))
        start += len(entries)
        if start >= total:
            break
        if not entries:
            raise RuntimeError("Incomplete arXiv page")


# ACM publications

def search_acm(query, config):
    start = 0
    while True:
        data = get(config["api_url"], {
            "query.bibliographic": query, "filter": f'member:{config["member_id"]}',
            "rows": PAGE_SIZE, "offset": start,
        }).json()["message"]
        items = data.get("items", [])
        for item in items:
            date_parts = (item.get("published-print") or item.get("published-online")
                          or item.get("issued") or {}).get("date-parts", [[]])
            yield {
                "title": " ".join(item.get("title", [])), "doi": item.get("DOI", ""),
                "year": str(date_parts[0][0]) if date_parts and date_parts[0] else "",
                "authors": "; ".join(" ".join(filter(None, [a.get("given"), a.get("family")]))
                                     for a in item.get("author", [])),
                "venue": " ".join(item.get("container-title", [])),
                "abstract": item.get("abstract", ""), "type": item.get("type", ""),
                "url": item.get("URL", ""),
            }
        start += len(items)
        if start >= int(data["total-results"]):
            break
        if not items:
            raise RuntimeError("Incomplete ACM page")


# DBLP


def search_dblp(query, config):
    start = 0
    while True:
        data = get(config["api_url"], {"q": query, "format": "json", "h": PAGE_SIZE, "f": start}).json()
        hits = data["result"]["hits"]
        items = hits.get("hit", [])
        if isinstance(items, dict):
            items = [items]
        for item in items:
            info = item["info"]
            authors = info.get("authors", {}).get("author", [])
            if not isinstance(authors, list):
                authors = [authors]
            authors = "; ".join(a.get("text", "") if isinstance(a, dict) else a for a in authors)
            yield {**info, "authors": authors, "dblp_key": info.get("key", "")}
        start += len(items)
        if start >= int(hits["@total"]):
            break
        if not items:
            raise RuntimeError("Incomplete DBLP page")


# Elsevier Scopus

def search_scopus(query, config):
    start = 0
    headers = {"X-ELS-APIKey": config["api_key"], "Accept": "application/json"}
    if config["inst_token"]:
        headers["X-ELS-Insttoken"] = config["inst_token"]
    while True:
        data = get(config["api_url"], {"query": query, "count": PAGE_SIZE, "start": start},
                   headers).json()
        results = data["search-results"]
        total = int(results["opensearch:totalResults"])
        if total == 0:
            break
        items = results.get("entry", [])
        for item in items:
            links = item.get("link", [])
            if isinstance(links, dict):
                links = [links]
            yield {
                "title": item.get("dc:title", ""), "doi": item.get("prism:doi", ""),
                "year": item.get("prism:coverDate", "")[:4],
                "authors": item.get("dc:creator", ""), "venue": item.get("prism:publicationName", ""),
                "type": item.get("subtypeDescription", ""), "abstract": item.get("dc:description", ""),
                "url": next((link.get("@href", "") for link in links if link.get("@ref") == "scopus"), ""),
            }
        start += len(items)
        if start >= total:
            break
        if not items:
            raise RuntimeError("Incomplete Scopus page")


# Springer Nature

def search_springer(query, config):
    start = 1
    while True:
        data = get(config["api_url"], {
            "api_key": config["api_key"], "q": query, "p": PAGE_SIZE, "s": start,
        }).json()
        records = data.get("records", [])
        for record in records:
            yield {
                "title": record.get("title", ""), "doi": record.get("doi", ""),
                "year": record.get("publicationDate", "")[:4],
                "authors": record.get("creators", ""),
                "venue": record.get("publicationName", "") or record.get("journalTitle", ""),
                "type": record.get("contentType", ""),
                "abstract": record.get("abstract", ""), "url": record.get("url", ""),
            }
        result = data.get("result", [{}])[0]
        total = int(result.get("total", len(records)))
        start += len(records)
        if start > total:
            break
        if not records:
            raise RuntimeError("Incomplete Springer page")


SEARCHERS = {
    "ieee": search_ieee, "scopus": search_scopus, "acm": search_acm,
    "dblp": search_dblp, "arxiv": search_arxiv, "springer": search_springer,
}


def collect_online(platform):
    records = []
    for query in queries(platform):
        print(f"{platform}: {query}")
        for item in SEARCHERS[platform](query, PLATFORMS[platform]):
            record = normalize_record(item, platform)
            record["query"] = query
            record["dblp_key"] = item.get("dblp_key", "")
            records.append(record)
    return records


def fetch_bibtex(records, template):
    cache = {}
    for record in records:
        if record["bibtex"]:
            continue
        doi, key = record["doi"], record.get("dblp_key", "")
        if ("{doi}" in template and not doi) or ("{key}" in template and not key):
            continue
        url = template.format(doi=quote(doi, safe="/"), key=quote(key, safe="/"))
        if url not in cache:
            cache[url] = get(url, headers={"Accept": "application/x-bibtex"}).text.strip()
        record["bibtex"] = cache[url]


def deduplicate(records):
    selected, seen = [], set()
    for record in records:
        identifier = ("doi", record["doi"]) if record["doi"] else (
            ("url", record["url"]) if record["url"] else None)
        if identifier is None or identifier not in seen:
            selected.append(record)
            seen.add(identifier)
    return selected


def export(records, platform, output):
    pd.DataFrame(records, columns=FIELDS).to_csv(output / f"{platform}_raw.csv", index=False, encoding="utf-8-sig")
    selected = deduplicate(records)
    pd.DataFrame(selected, columns=FIELDS).to_csv(output / f"{platform}_papers.csv", index=False, encoding="utf-8-sig")
    print(f"{platform}: {len(records)} records; {len(selected)} after DOI/URL deduplication")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=[*PLATFORMS, "all"], required=True)
    parser.add_argument("--input", type=Path, nargs="+", help="Google Scholar export files")
    parser.add_argument("--output", type=Path, default=Path("results"))
    parser.add_argument("--encoding", default="utf-8-sig")
    parser.add_argument("--columns", help="Comma-separated column names for files without a header")
    parser.add_argument("--fetch-bibtex", action="store_true")
    args = parser.parse_args()
    platforms = list(PLATFORMS) if args.platform == "all" else [args.platform]
    if "google" in platforms and not args.input:
        parser.error("Google Scholar requires --input")
    args.output.mkdir(parents=True, exist_ok=True)
    for platform in platforms:
        if platform != "google":
            records = collect_online(platform)
        else:
            records = import_records(args.input, platform, args.encoding,
                                     args.columns.split(",") if args.columns else None)
        if args.fetch_bibtex:
            fetch_bibtex(records, PLATFORMS[platform].get("bibtex_url") or DOI_BIBTEX_URL)
        export(records, platform, args.output)


if __name__ == "__main__":
    main()
