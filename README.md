# Secure Code Review Survey

Data and collection code for the secure code review survey.

## Contents

- `collect_papers.py`: unified collection and import script.
- `requirements.txt`: Python dependencies.
- `data/c0.csv`–`data/c4.csv`: screening-stage records.
- `data/final_included_36.csv`: final included studies.

## Setup

Requires Python 3.9 or later.

```bash
python -m pip install -r requirements.txt
```

## Platforms

| Platform | Identifier | Collection mode |
|---|---|---|
| Google Scholar | `google` | Import |
| IEEE Xplore | `ieee` | Metadata API |
| Elsevier Scopus | `scopus` | Search API |
| ACM Digital Library | `acm` | Crossref metadata API |
| DBLP | `dblp` | Search API |
| arXiv | `arxiv` | Public Atom API |
| SpringerLink | `springer` | Springer Nature Metadata API |

Configure the fields in `PLATFORMS` at the top of `collect_papers.py`:

- **IEEE Xplore:** `api_url` and `api_key`.
- **Scopus:** `api_url`, `api_key`, and optional `inst_token`.
- **ACM Digital Library:** Crossref `api_url`; `member_id` is set to ACM.
- **DBLP:** `api_url` and optional `bibtex_url` using `{key}`.
- **arXiv:** `api_url`.
- **SpringerLink:** `api_url`, `api_key`, and optional `bibtex_url` using `{doi}`.
- **Google Scholar:** exported result files.

For DOI-based BibTeX retrieval, set `DOI_BIBTEX_URL` with a `{doi}` placeholder.

## Usage

### Online collection

```bash
python collect_papers.py --platform ieee --output results/ieee
python collect_papers.py --platform arxiv --output results/arxiv
python collect_papers.py --platform acm --output results/acm
```

Use `--fetch-bibtex` to retrieve BibTeX entries.

### Import Google Scholar results

```bash
python collect_papers.py --platform google --input imports/google/papers.xlsx --output results/google
```

Supported formats: CSV, XLSX and JSON. Multiple files can be listed after `--input`. Use `--encoding` to specify the CSV encoding and `--columns title,url,year` to supply column names.

### Collect all platforms

Configure the six online platforms and supply the Google Scholar export:

```bash
python collect_papers.py --platform all --input imports/google/papers.xlsx --output results
```

## Output

- `<platform>_raw.csv`: collected records.
- `<platform>_papers.csv`: records deduplicated by DOI or URL.

Output files use UTF-8 encoding with BOM.
