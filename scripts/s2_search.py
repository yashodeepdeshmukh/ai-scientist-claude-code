#!/usr/bin/env python3
"""Literature search for novelty checks and citations.

Engines:
  auto (default)             Semantic Scholar, falling back to OpenAlex on errors / rate limits
  semanticscholar            https://api.semanticscholar.org  (set S2_API_KEY for higher rate limits)
  openalex                   https://api.openalex.org          (no key needed)

Usage:
  s2_search.py "query text" [--limit 10] [--engine semanticscholar|openalex] [--format text|json]

Text format prints a numbered list the model can read. JSON format includes the BibTeX entry
for each paper so the writer can paste it into references.bib.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

S2_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_FIELDS = "title,authors,venue,year,abstract,citationStyles,citationCount"
OA_URL = "https://api.openalex.org/works"
UA = {"User-Agent": "ai-scientist-claude-plugin/0.1"}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _get(url, headers, retries=3):
    opener = urllib.request.build_opener(NoRedirect())
    delay = 1.0
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with opener.open(req, timeout=15) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise
        except urllib.error.URLError:
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise
    return {}


def search_s2(query, limit):
    headers = dict(UA)
    key = os.environ.get("S2_API_KEY")
    if key:
        headers["X-API-KEY"] = key
    params = urllib.parse.urlencode({"query": query, "limit": limit, "fields": S2_FIELDS})
    data = _get(f"{S2_URL}?{params}", headers)
    out = []
    for p in data.get("data") or []:
        out.append({
            "title": p.get("title"),
            "authors": ", ".join(a.get("name", "") for a in (p.get("authors") or [])),
            "venue": p.get("venue"),
            "year": p.get("year"),
            "citationCount": p.get("citationCount"),
            "abstract": p.get("abstract"),
            "bibtex": (p.get("citationStyles") or {}).get("bibtex"),
        })
    return out


def _oa_abstract(inv):
    if not inv:
        return None
    pos = []
    for word, idxs in inv.items():
        for i in idxs:
            pos.append((i, word))
    return " ".join(w for _, w in sorted(pos))


def _tex(v):
    """Escape LaTeX special characters that commonly appear in titles."""
    return re.sub(r"(?<!\\)([&%#_])", r"\\\1", v)


def _oa_bibtex(w, authors):
    first = (authors[0].split()[-1] if authors else "anon").lower()
    first = re.sub(r"[^a-z]", "", first) or "anon"
    year = w.get("publication_year") or ""
    word = re.sub(r"[^a-z]", "", ((w.get("title") or "x").split() or ["x"])[0].lower()) or "x"
    key = f"{first}{year}{word}"
    venue = ((w.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
    fields = {
        "title": w.get("title") or "",
        "author": " and ".join(authors),
        "year": str(year),
        "journal": venue,
    }
    if w.get("doi"):
        fields["doi"] = w["doi"].replace("https://doi.org/", "")
    body = ",\n".join(f"  {k} = {{{v if k == 'doi' else _tex(v)}}}" for k, v in fields.items() if v)
    return f"@article{{{key},\n{body}\n}}"


def search_openalex(query, limit):
    params = urllib.parse.urlencode({"search": query, "per-page": limit})
    data = _get(f"{OA_URL}?{params}", dict(UA))
    out = []
    for w in data.get("results") or []:
        authors = [a.get("author", {}).get("display_name", "") for a in (w.get("authorships") or [])]
        out.append({
            "title": w.get("title"),
            "authors": ", ".join(authors),
            "venue": ((w.get("primary_location") or {}).get("source") or {}).get("display_name"),
            "year": w.get("publication_year"),
            "citationCount": w.get("cited_by_count"),
            "abstract": _oa_abstract(w.get("abstract_inverted_index")),
            "bibtex": _oa_bibtex(w, authors),
        })
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--engine", choices=["auto", "semanticscholar", "openalex"],
                    default=os.environ.get("AI_SCIENTIST_SEARCH_ENGINE", "auto"))
    ap.add_argument("--format", choices=["text", "json"], default="text")
    args = ap.parse_args()

    engines = ["semanticscholar", "openalex"] if args.engine == "auto" else [args.engine]
    papers, errors = None, []
    for eng in engines:
        try:
            papers = search_s2(args.query, args.limit) if eng == "semanticscholar" \
                else search_openalex(args.query, args.limit)
            if len(engines) > 1 and eng != engines[0]:
                print(f"(fell back to {eng}: {errors[-1]})", file=sys.stderr)
            break
        except urllib.error.HTTPError as error:
            errors.append(f"{eng}: HTTP {error.code}")
        except (OSError, ValueError, TypeError, AttributeError) as error:
            errors.append(f"{eng}: {type(error).__name__}")
    if papers is None:
        print("SEARCH_ERROR " + "; ".join(errors), file=sys.stderr)
        sys.exit(2)

    if args.format == "json":
        print(json.dumps(papers, indent=2))
        return
    if not papers:
        print("No papers found.")
        return
    for i, p in enumerate(papers):
        abstract = (p.get("abstract") or "No abstract available.").replace("\n", " ")
        print(f"{i}: {p['title']}. {p['authors']}. {p.get('venue') or ''}, {p.get('year')}.\n"
              f"Number of citations: {p.get('citationCount')}\nAbstract: {abstract}\n")


if __name__ == "__main__":
    main()
