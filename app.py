from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from threading import Lock, Thread
from time import sleep
from typing import Any
import re
import os
from urllib.parse import quote_plus

from flask import Flask, jsonify, request

# ── Importe les vraies sources (remplace les mocks) ──
from sources import fetch_jobs_for_source, AVAILABLE_SOURCES

app = Flask(__name__)

BACKEND_VERSION = "jobradar-real-sources-v1"


@app.after_request
def add_cors_headers(response: Any) -> Any:
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


LOCATION_LIBRARY = [
    "Remote", "Remote - Europe", "Barcelona, Spain", "Madrid, Spain",
    "Paris, France", "London, United Kingdom", "Dublin, Ireland",
    "Berlin, Germany", "Amsterdam, Netherlands",
    "Zurich, Switzerland", "Geneva, Switzerland",
]

ROLE_FAMILIES: dict[str, list[str]] = {
    "sales": ["sales", "commercial", "new business", "closing", "inside sales"],
    "account executive": ["account executive", "ae", "mid-market account executive", "enterprise account executive"],
    "key account manager": ["key account manager", "strategic account manager", "global account manager"],
    "account manager": ["account manager", "client partner", "relationship manager", "portfolio manager"],
    "customer success": ["customer success", "csm", "client success", "retention", "renewals", "onboarding", "implementation"],
    "business development": ["business development", "bdr", "sdr", "sales development", "prospecting", "pipeline"],
    "partnerships": ["partnerships", "channel partnerships", "alliances", "partner manager", "ecosystem"],
    "revenue operations": ["revenue operations", "revops", "sales operations", "gtm operations", "forecasting", "crm"],
    "business operations": ["business operations", "bizops", "operations associate", "operations manager"],
    "growth": ["growth", "growth manager", "growth marketing", "acquisition", "activation"],
    "marketing": ["marketing", "demand generation", "field marketing", "campaign", "content marketing"],
    "product marketing": ["product marketing", "positioning", "messaging", "launch", "sales enablement"],
    "brand management": ["brand manager", "brand management", "brand marketing", "trade marketing"],
    "strategy": ["strategy", "strategy associate", "commercial strategy", "go-to-market", "pricing"],
    "consulting": ["consulting", "consultant", "management consultant"],
    "business analyst": ["business analyst", "commercial analyst", "analyst", "kpi", "performance analysis"],
    "project management": ["project manager", "program manager", "stakeholder management"],
}

DEFAULT_SCAN_PAYLOAD: dict[str, Any] = {
    "filters": {
        "keywords": list(ROLE_FAMILIES.keys()),
        "exclude": ["intern", "internship", "director", "vp", "head of", "chief"],
        "locations": ["switzerland", "barcelona", "madrid", "paris", "london", "berlin", "amsterdam", "dublin", "remote"],
        "levels": ["junior", "mid", "senior"],
        "sources": AVAILABLE_SOURCES,
        "companies": [],
    },
    "weights": {
        "keywords": 40,
        "location": 20,
        "company": 10,
        "semantic": 30,
    },
    "display": {
        "limit": 80,
        "min_score": 12,
    },
}

scan_lock = Lock()
scan_state: dict[str, Any] = {
    "running": False,
    "progress": 0,
    "status": "Idle",
    "count": 0,
    "sources": AVAILABLE_SOURCES,
    "jobs": [],
    "raw_jobs": [],
    "request": deepcopy(DEFAULT_SCAN_PAYLOAD),
}


@dataclass
class ScanContext:
    filters: dict[str, list[str]]
    weights: dict[str, int | float]
    display: dict[str, int | float]


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def normalize_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [normalize_text(item) for item in values if normalize_text(item)]


def build_context(payload: dict[str, Any]) -> ScanContext:
    filters = payload.get("filters", {})
    weights = payload.get("weights", {})
    display = payload.get("display", {})
    requested_sources = [str(item).strip() for item in filters.get("sources", []) if str(item).strip()]
    return ScanContext(
        filters={
            "keywords": normalize_list(filters.get("keywords")),
            "exclude": normalize_list(filters.get("exclude")),
            "locations": normalize_list(filters.get("locations")),
            "levels": normalize_list(filters.get("levels")),
            "sources": requested_sources,
            "companies": normalize_list(filters.get("companies")),
        },
        weights={
            "keywords": float(weights.get("keywords", 40)),
            "location": float(weights.get("location", 20)),
            "company": float(weights.get("company", 10)),
            "semantic": float(weights.get("semantic", 30)),
        },
        display={
            "limit": int(display.get("limit", 80)),
            "min_score": float(display.get("min_score", 12)),
        },
    )


def normalize_job(job: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "company":     str(job.get("company", "")).strip(),
        "position":    str(job.get("position", "")).strip(),
        "location":    str(job.get("location", "")).strip(),
        "link":        str(job.get("link", "")).strip(),
        "source":      str(job.get("source", "")).strip(),
        "description": str(job.get("description", "")).strip(),
        "level":       str(job.get("level", "mid")).strip().lower() or "mid",
    }
    normalized["score_breakdown"] = {"keywords": 0, "location": 0, "company": 0, "semantic": 0, "final": 0}
    return normalized


def job_search_blob(job: dict[str, Any]) -> str:
    return " ".join([
        job.get("company", ""), job.get("position", ""),
        job.get("location", ""), job.get("description", ""),
    ]).lower()


def expand_keywords(keywords: list[str]) -> list[str]:
    expanded: set[str] = set()
    for keyword in keywords:
        nk = normalize_text(keyword)
        if not nk:
            continue
        expanded.add(nk)
        for family, terms in ROLE_FAMILIES.items():
            if nk == family or nk in terms:
                expanded.add(family)
                expanded.update(terms)
    return sorted(expanded)


def job_matches_filters(job: dict[str, Any], filters: dict[str, list[str]]) -> bool:
    source_filter = filters.get("sources", [])
    if source_filter and job.get("source") not in source_filter:
        return False
    blob = job_search_blob(job)
    if any(term in blob for term in filters.get("exclude", [])):
        return False
    return True


def compute_keyword_score(job, keywords, expanded) -> float:
    if not keywords:
        return 0.0
    title = normalize_text(job.get("position"))
    description = normalize_text(job.get("description"))
    score = 0.0
    if any(normalize_text(t) in title for t in keywords):
        score = max(score, 92.0)
    if any(t in title for t in expanded):
        score = max(score, 78.0)
    if any(normalize_text(t) in description for t in keywords):
        score = max(score, 58.0)
    if any(t in description for t in expanded):
        score = max(score, 42.0)
    title_hits = sum(1 for t in expanded if t in title)
    desc_hits  = sum(1 for t in expanded if t in description)
    score += min(22.0, title_hits * 4.0 + desc_hits * 1.5)
    return min(100.0, score)


def compute_location_score(job, locations) -> float:
    if not locations:
        return 0.0
    jl = normalize_text(job.get("location"))
    if not jl:
        return 0.0
    best = 0.0
    for loc in locations:
        if loc == jl:
            best = max(best, 100.0)
        elif loc in jl:
            best = max(best, 82.0)
        elif loc == "remote" and "remote" in jl:
            best = max(best, 92.0)
    return best


def compute_company_score(job, companies) -> float:
    if not companies:
        return 0.0
    c = normalize_text(job.get("company"))
    if c in companies:
        return 100.0
    if any(t in c for t in companies):
        return 72.0
    return 0.0


def compute_semantic_score(job, expanded) -> float:
    if not expanded:
        return 0.0
    title = normalize_text(job.get("position"))
    desc  = normalize_text(job.get("description"))
    overlap = sum(1 for t in expanded if t in title or t in desc)
    denom = max(8, int(len(expanded) * 0.32))
    return min(100.0, (overlap / denom) * 100.0)


def compute_final_score(job, filters, weights) -> dict[str, float]:
    keywords = filters.get("keywords", [])
    expanded = expand_keywords(keywords)
    kw_s   = compute_keyword_score(job, keywords, expanded)
    loc_s  = compute_location_score(job, filters.get("locations", []))
    com_s  = compute_company_score(job, filters.get("companies", []))
    sem_s  = compute_semantic_score(job, expanded)
    parts = []
    if filters.get("keywords"):
        parts.append((kw_s,  float(weights.get("keywords", 0))))
        parts.append((sem_s, float(weights.get("semantic", 0))))
    if filters.get("locations"):
        parts.append((loc_s, float(weights.get("location", 0))))
    if filters.get("companies"):
        parts.append((com_s, float(weights.get("company", 0))))
    total_w = sum(w for _, w in parts)
    final   = sum(s * w for s, w in parts) / total_w if total_w else kw_s
    return {
        "keywords": round(kw_s, 2),
        "location": round(loc_s, 2),
        "company":  round(com_s, 2),
        "semantic": round(sem_s, 2),
        "final":    round(final, 2),
    }


def deduplicate_jobs(jobs):
    seen, deduped = set(), []
    for job in jobs:
        link = job.get("link")
        if not link or link in seen:
            continue
        seen.add(link)
        deduped.append(job)
    return deduped


def update_scan_state(**kwargs):
    with scan_lock:
        scan_state.update(kwargs)


def run_scan(payload: dict[str, Any]) -> None:
    context = build_context(payload)
    active_sources = context.filters["sources"] or AVAILABLE_SOURCES
    collected: list[dict] = []

    update_scan_state(
        running=True, progress=0, status="Initialisation...",
        count=0, sources=active_sources, jobs=[], raw_jobs=[],
        request=deepcopy(payload),
    )

    total_steps = max(len(active_sources), 1) + 4

    for index, source in enumerate(active_sources, start=1):
        update_scan_state(
            status=f"Scan {source}...",
            progress=int((index - 1) / total_steps * 100),
        )
        new_jobs = fetch_jobs_for_source(source)
        collected.extend([normalize_job(j) for j in new_jobs])
        update_scan_state(count=len(collected))

    update_scan_state(status="Dédoublonnage...", progress=int(len(active_sources) / total_steps * 100))
    deduped = deduplicate_jobs(collected)

    update_scan_state(status="Filtrage...", progress=int((len(active_sources) + 1) / total_steps * 100))
    filtered = [j for j in deduped if job_matches_filters(j, context.filters)]

    update_scan_state(status="Scoring...", progress=int((len(active_sources) + 2) / total_steps * 100))
    scored = []
    for job in filtered:
        job["score_breakdown"] = compute_final_score(job, context.filters, context.weights)
        scored.append(job)

    scored.sort(key=lambda x: x["score_breakdown"]["final"], reverse=True)

    update_scan_state(
        running=False, progress=100,
        status=f"Terminé — {len(scored)} offres trouvées",
        count=len(scored), jobs=scored,
    )


@app.get("/")
def index():
    return jsonify({"status": "JobRadar API running", "version": BACKEND_VERSION, "sources": AVAILABLE_SOURCES})


@app.get("/health")
def health():
    return jsonify({"ok": True, "version": BACKEND_VERSION, "sources": len(AVAILABLE_SOURCES)})


@app.post("/scan")
def start_scan():
    with scan_lock:
        if scan_state["running"]:
            return jsonify({"message": "Scan déjà en cours"}), 409
        scan_state["running"] = True
    raw = request.get_json(silent=True)
    payload = deepcopy(raw) if raw else deepcopy(DEFAULT_SCAN_PAYLOAD)
    Thread(target=run_scan, args=(payload,), daemon=True).start()
    return jsonify({"message": "Scan démarré", "version": BACKEND_VERSION}), 202


@app.get("/status")
def get_status():
    with scan_lock:
        return jsonify({
            "version":  BACKEND_VERSION,
            "running":  scan_state["running"],
            "progress": scan_state["progress"],
            "status":   scan_state["status"],
            "count":    scan_state["count"],
            "sources":  scan_state["sources"],
        })


@app.get("/jobs")
def get_jobs():
    limit_arg     = request.args.get("limit")
    min_score_arg = request.args.get("min_score")
    levels_arg    = request.args.get("levels", "")
    sources_arg   = request.args.get("sources", "")

    with scan_lock:
        jobs    = deepcopy(scan_state["jobs"])
        req_pay = deepcopy(scan_state["request"])

    limit     = int(limit_arg)     if limit_arg     else int(req_pay["display"].get("limit",     80))
    min_score = float(min_score_arg) if min_score_arg else float(req_pay["display"].get("min_score", 12))

    req_levels  = {normalize_text(l) for l in levels_arg.split(",")  if normalize_text(l)}
    req_sources = {s.strip()         for s in sources_arg.split(",") if s.strip()}

    visible = [j for j in jobs if j["score_breakdown"]["final"] >= min_score]
    if req_levels:
        visible = [j for j in visible if normalize_text(j.get("level")) in req_levels]
    if req_sources:
        visible = [j for j in visible if j.get("source") in req_sources]

    return jsonify({"jobs": visible[:limit]})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
