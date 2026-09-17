# Secure Code Review Survey Reproduction Package

This repository contains the reproduction package for the systematic
survey:

**Secure Code Review: A Systematic Survey of Technical Tasks,
Mechanisms, and Evaluation**

The artifact provides the materials used throughout the systematic
review process, including:

-   automated literature collection scripts;
-   bibliographic records collected from multiple sources;
-   intermediate screening results;
-   the final set of included studies;
-   quality guideline search (QGS) materials.

------------------------------------------------------------------------

## Repository Structure

``` text
reproduction_package/
│
├── data/
│   ├── collect_papers.py
│   ├── ACM/
│   ├── DBLP/
│   ├── Elsevier scopus/
│   ├── google/
│   ├── ieee/
│   ├── springer/
│   ├── arxiv/
│   ├── F0.csv
│   ├── F1.csv
│   ├── F2.csv
│   ├── F3.csv
│   ├── F4.csv
│   ├── F5.csv
│   └── final_included_36.csv
│
├── QGS_Five_Papers/
│   ├── five_papers.xlsx
│   └── 12 venues paper/
│
├── requirements.txt
├── LICENSE
└── README.md
```

------------------------------------------------------------------------

# 1. Literature Collection

The `data/collect_papers.py` script provides a unified framework for
collecting bibliographic records from multiple academic sources.

The script supports:

-   querying multiple literature databases;
-   importing exported search results;
-   metadata normalization;
-   DOI extraction and normalization;
-   duplicate removal;
-   BibTeX retrieval.

The collected raw records are organized according to different sources:

  Directory            Source
  -------------------- ------------------------
  `ACM/`               ACM-related records
  `DBLP/`              DBLP records
  `Elsevier scopus/`   Scopus records
  `google/`            Google Scholar records
  `ieee/`              IEEE Xplore records
  `springer/`          SpringerLink records
  `arxiv/`             arXiv records

------------------------------------------------------------------------

# 2. Environment Setup

The reproduction package requires:

-   Python 3.9 or later

Install dependencies:

``` bash
pip install -r requirements.txt
```

------------------------------------------------------------------------

# 3. Literature Screening

The screening process contains multiple stages.

Intermediate screening results are provided as:

``` text
data/
├── F0.csv
├── F1.csv
├── F2.csv
├── F3.csv
├── F4.csv
└── F5.csv
```

These files record the intermediate filtering process of the systematic
review.

The final included studies are provided in:

``` text
data/final_included_36.csv
```

which contains the 36 studies included in the final survey.

------------------------------------------------------------------------

# 4. Quality Guideline Search (QGS)

To evaluate the completeness of the search strategy, additional quality
guideline searches were conducted.

The QGS materials are provided in:

``` text
QGS_Five_Papers/

├── five_papers.xlsx
└── 12 venues paper/
```

The `12 venues paper` directory contains papers collected from
representative software engineering and security venues, including:

-   ICSE
-   FSE
-   ASE
-   ISSTA
-   TSE
-   TOSEM
-   TDSC
-   TIFS
-   S&P
-   NDSS
-   USS

These materials are used to verify whether the search strategy can
identify representative secure code review studies.

------------------------------------------------------------------------

# 5. Configuration

Before running online collection, configure the required API information
in:

``` text
data/collect_papers.py
```

The script supports configuration for different data sources, including:

-   IEEE Xplore API;
-   Scopus API;
-   Springer metadata API;
-   DBLP endpoint;
-   arXiv API;
-   DOI-based BibTeX retrieval.

Google Scholar records can be imported from exported files.

------------------------------------------------------------------------

# 6. Usage

Example: collect records from IEEE Xplore:

``` bash
python collect_papers.py --platform ieee --output results/ieee
```

Example: import Google Scholar records:

``` bash
python collect_papers.py \
--platform google \
--input papers.xlsx \
--output results/google
```

The generated outputs include raw records and processed bibliographic
records.

------------------------------------------------------------------------

# 7. License

This project is released under the LICENSE included in this repository.
