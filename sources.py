"""
sources.py — Vraies sources de jobs pour JobRadar
Remplace les données fictives de build_mock_source_data()
"""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from typing import Any

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
TIMEOUT = 15


# ── Helpers ────────────────────────────────────────────────────────────────

def safe_get(url: str, **kwargs) -> requests.Response | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, **kwargs)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"[sources] GET {url} → {e}")
        return None


def make_job(source: str, company: str, position: str, location: str,
             link: str, description: str = "") -> dict[str, Any]:
    return {
        "company":     company.strip(),
        "position":    position.strip(),
        "location":    location.strip(),
        "link":        link.strip(),
        "source":      source,
        "description": description.strip()[:800],
        "level":       infer_level(position),
    }


def infer_level(position: str) -> str:
    t = position.lower()
    if any(x in t for x in ["enterprise", "strategic", "senior", "lead", "director", "head"]):
        return "senior"
    if any(x in t for x in ["associate", "specialist", "representative", "analyst", "coordinator", "junior", "graduate", "trainee"]):
        return "junior"
    return "mid"


# ── Greenhouse ─────────────────────────────────────────────────────────────

GREENHOUSE_COMPANIES = [
    "typeform", "gitlab", "remote", "notion", "figma",
    "intercom", "zendesk", "hubspot", "datadog", "miro",
]

def fetch_greenhouse() -> list[dict]:
    jobs = []
    for company in GREENHOUSE_COMPANIES:
        r = safe_get(f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs")
        if not r:
            continue
        for job in r.json().get("jobs", []):
            jobs.append(make_job(
                source="Greenhouse",
                company=company.capitalize(),
                position=job.get("title", ""),
                location=job.get("location", {}).get("name", ""),
                link=job.get("absolute_url", ""),
                description=job.get("title", ""),
            ))
        print(f"greenhouse/{company}: {len(jobs)} total")
    return jobs


# ── Lever ──────────────────────────────────────────────────────────────────

LEVER_COMPANIES = [
    "applydigital", "deliveroo", "monzo", "wise", "pleo",
    "personio", "mollie", "spendesk", "qonto", "payfit",
]

def fetch_lever() -> list[dict]:
    jobs = []
    for company in LEVER_COMPANIES:
        r = safe_get(f"https://api.lever.co/v0/postings/{company}?mode=json")
        if not r:
            continue
        for job in r.json():
            cats = job.get("categories", {})
            jobs.append(make_job(
                source="Lever",
                company=company.capitalize(),
                position=job.get("text", ""),
                location=cats.get("location", ""),
                link=job.get("hostedUrl", ""),
                description=job.get("text", ""),
            ))
        print(f"lever/{company}: {len(jobs)} total")
    return jobs


# ── Ashby ──────────────────────────────────────────────────────────────────

ASHBY_COMPANIES = [
    "ramp", "replit", "openai", "airtable", "linear",
    "retool", "mercury", "rippling", "deel", "brex",
]

def fetch_ashby() -> list[dict]:
    jobs = []
    for company in ASHBY_COMPANIES:
        r = safe_get(f"https://api.ashbyhq.com/posting-api/job-board/{company}")
        if not r:
            continue
        for job in r.json().get("jobs", []):
            jobs.append(make_job(
                source="Ashby",
                company=company.capitalize(),
                position=job.get("title", ""),
                location=job.get("location", ""),
                link=job.get("jobUrl", ""),
                description=job.get("title", ""),
            ))
        print(f"ashby/{company}: {len(jobs)} total")
    return jobs


# ── RemoteOK ───────────────────────────────────────────────────────────────

def fetch_remoteok() -> list[dict]:
    r = safe_get("https://remoteok.com/api")
    if not r:
        return []
    jobs = []
    for job in r.json()[1:]:
        tags = job.get("tags", [])
        jobs.append(make_job(
            source="RemoteOK",
            company=job.get("company", ""),
            position=job.get("position", ""),
            location=job.get("location", "Remote"),
            link=job.get("url", ""),
            description=job.get("description", "") or str(tags),
        ))
    print(f"remoteok: {len(jobs)} offres")
    return jobs


# ── We Work Remotely (RSS) ─────────────────────────────────────────────────

WWR_FEEDS = {
    "business":  "https://weworkremotely.com/categories/remote-business-exec-management-jobs.rss",
    "sales":     "https://weworkremotely.com/categories/remote-sales-jobs.rss",
    "marketing": "https://weworkremotely.com/categories/remote-marketing-jobs.rss",
}

def fetch_wwr() -> list[dict]:
    jobs = []
    for category, url in WWR_FEEDS.items():
        r = safe_get(url)
        if not r:
            continue
        try:
            root = ET.fromstring(r.content)
        except Exception:
            continue
        channel = root.find("channel")
        if not channel:
            continue
        for item in channel.findall("item"):
            title = item.findtext("title", "").strip()
            link  = item.findtext("link", "").strip()
            desc  = re.sub(r"<[^>]+>", " ", item.findtext("description", ""))
            if ": " in title:
                company, position = title.split(": ", 1)
            else:
                company, position = "Unknown", title
            jobs.append(make_job(
                source="We Work Remotely",
                company=company,
                position=position,
                location="Remote",
                link=link,
                description=desc[:500],
            ))
    print(f"wwr: {len(jobs)} offres")
    return jobs


# ── Himalayas ──────────────────────────────────────────────────────────────

def fetch_himalayas() -> list[dict]:
    r = safe_get("https://himalayas.app/jobs/api", params={"limit": 100})
    if not r:
        return []
    jobs = []
    for job in r.json().get("jobs", []):
        loc = job.get("locationRestrictions", [])
        location = ", ".join(loc) if isinstance(loc, list) and loc else "Remote"
        jobs.append(make_job(
            source="Himalayas",
            company=job.get("companyName", ""),
            position=job.get("title", ""),
            location=location,
            link=f"https://himalayas.app/jobs/{job.get('slug', '')}",
            description=job.get("description", "")[:500],
        ))
    print(f"himalayas: {len(jobs)} offres")
    return jobs


# ── Hacker News Who's Hiring ───────────────────────────────────────────────

RELEVANT_KEYWORDS = [
    "customer success", "account manager", "account executive",
    "business development", "partnerships", "csm", "client success",
    "growth", "sales", "relationship manager", "post-sales",
]

def fetch_hn() -> list[dict]:
    r = safe_get(f"https://hacker-news.firebaseio.com/v0/user/whoishiring.json")
    if not r:
        return []
    thread_id = r.json().get("submitted", [None])[0]
    if not thread_id:
        return []
    thread = safe_get(f"https://hacker-news.firebaseio.com/v0/item/{thread_id}.json")
    if not thread:
        return []
    kids = thread.json().get("kids", [])[:200]
    jobs = []
    for kid_id in kids:
        item = safe_get(f"https://hacker-news.firebaseio.com/v0/item/{kid_id}.json")
        if not item:
            continue
        data = item.json()
        if not data or data.get("deleted") or data.get("dead"):
            continue
        text = re.sub(r"<[^>]+>", " ", data.get("text", "") or "")
        if not any(kw in text.lower() for kw in RELEVANT_KEYWORDS):
            continue
        lines = [l.strip() for l in text.split("|") if l.strip()]
        company  = lines[0][:80] if lines else "HN Company"
        position = lines[1][:120] if len(lines) > 1 else "See post"
        jobs.append(make_job(
            source="Hacker News",
            company=company,
            position=position,
            location="Remote / Various",
            link=f"https://news.ycombinator.com/item?id={kid_id}",
            description=text[:600],
        ))
    print(f"hn: {len(jobs)} offres")
    return jobs


# ── Welcome to the Jungle ──────────────────────────────────────────────────

from urllib.parse import quote as urlquote
from bs4 import BeautifulSoup

WTTJ_SEARCHES = [
    ("customer success",    "barcelona"),
    ("account manager",     "paris"),
    ("business development","amsterdam"),
    ("customer success",    "remote"),
    ("account executive",   "berlin"),
    ("partnerships",        "zurich"),
]

def fetch_wttj() -> list[dict]:
    jobs = []
    seen = set()
    for keyword, location in WTTJ_SEARCHES:
        url = f"https://www.welcometothejungle.com/en/jobs?query={urlquote(keyword)}&aroundQuery={urlquote(location)}"
        r = safe_get(url)
        if not r:
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            text = a.get_text(" ", strip=True)
            if "/jobs/" not in href or len(text) < 8:
                continue
            full_link = href if href.startswith("http") else f"https://www.welcometothejungle.com{href}"
            if full_link in seen:
                continue
            seen.add(full_link)
            jobs.append(make_job(
                source="Welcome to the Jungle",
                company="WTTJ",
                position=text[:120],
                location=location,
                link=full_link,
                description=text,
            ))
    print(f"wttj: {len(jobs)} offres")
    return jobs


# ── LinkedIn (scraping léger, best-effort) ─────────────────────────────────

LINKEDIN_SEARCHES = [
    ("customer success manager",    "Switzerland"),
    ("account manager",             "Barcelona"),
    ("business development",        "Paris"),
    ("customer success",            "Amsterdam"),
    ("account executive",           "Berlin"),
    ("graduate program business",   "Europe"),
    ("partnerships manager",        "Remote"),
]

def fetch_linkedin() -> list[dict]:
    """
    Scrape LinkedIn Jobs sans authentification via l'endpoint public.
    Limite : 25 résultats par recherche, peut être bloqué par rate-limiting.
    """
    jobs = []
    seen = set()

    for keyword, location in LINKEDIN_SEARCHES:
        url = (
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            f"?keywords={urlquote(keyword)}&location={urlquote(location)}&start=0"
        )
        r = safe_get(url)
        if not r:
            time.sleep(2)
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.find_all("li")

        for card in cards:
            try:
                title_el   = card.find("h3")
                company_el = card.find("h4")
                loc_el     = card.find("span", class_=re.compile("job-search-card__location"))
                link_el    = card.find("a", href=True)

                if not title_el or not link_el:
                    continue

                position = title_el.get_text(strip=True)
                company  = company_el.get_text(strip=True) if company_el else "LinkedIn"
                loc      = loc_el.get_text(strip=True) if loc_el else location
                link     = link_el["href"].split("?")[0]

                if link in seen or len(position) < 4:
                    continue
                seen.add(link)

                jobs.append(make_job(
                    source="LinkedIn",
                    company=company,
                    position=position,
                    location=loc,
                    link=link,
                    description=f"{position} at {company} — {loc}",
                ))
            except Exception:
                continue

        print(f"linkedin/{keyword}/{location}: {len(jobs)} total")
        time.sleep(1.5)  # pause entre requêtes pour éviter le blocage

    return jobs


# ── YCombinator (Workatastartup) ───────────────────────────────────────────

YC_ROLES = ["customer success", "account manager", "business development", "sales", "growth"]

def fetch_yc() -> list[dict]:
    jobs = []
    for role in YC_ROLES:
        r = safe_get(
            "https://www.workatastartup.com/jobs",
            params={"q": role, "jobType": "fulltime"},
        )
        if not r:
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=re.compile(r"/companies/.+/jobs/")):
            href = a.get("href", "")
            title = a.get_text(strip=True)
            if not title or len(title) < 4:
                continue
            full_link = f"https://www.workatastartup.com{href}"
            jobs.append(make_job(
                source="YCombinator",
                company="YC Startup",
                position=title[:120],
                location="Remote / Various",
                link=full_link,
                description=title,
            ))
    print(f"yc: {len(jobs)} offres")
    return jobs


# ── Adzuna (optionnel, nécessite clé API) ─────────────────────────────────

import os

ADZUNA_APP_ID  = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")
ADZUNA_COUNTRIES = ["ch", "de", "fr", "nl", "es"]
ADZUNA_TERMS = ["customer success", "account manager", "business development"]

def fetch_adzuna() -> list[dict]:
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        print("adzuna: clés manquantes, source ignorée")
        return []
    jobs = []
    seen = set()
    for country in ADZUNA_COUNTRIES:
        for term in ADZUNA_TERMS:
            url = (
                f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
                f"?app_id={ADZUNA_APP_ID}&app_key={ADZUNA_APP_KEY}"
                f"&results_per_page=20&what={urlquote(term)}&content-type=application/json"
            )
            r = safe_get(url)
            if not r:
                continue
            for job in r.json().get("results", []):
                link = job.get("redirect_url", "")
                if link in seen:
                    continue
                seen.add(link)
                jobs.append(make_job(
                    source="Adzuna",
                    company=job.get("company", {}).get("display_name", ""),
                    position=job.get("title", ""),
                    location=job.get("location", {}).get("display_name", ""),
                    link=link,
                    description=job.get("description", "")[:500],
                ))
    print(f"adzuna: {len(jobs)} offres")
    return jobs


# ── Dispatcher principal ───────────────────────────────────────────────────

SOURCE_FETCHERS: dict[str, Any] = {
    "Greenhouse":           fetch_greenhouse,
    "Lever":                fetch_lever,
    "Ashby":                fetch_ashby,
    "RemoteOK":             fetch_remoteok,
    "We Work Remotely":     fetch_wwr,
    "Himalayas":            fetch_himalayas,
    "Hacker News":          fetch_hn,
    "Welcome to the Jungle": fetch_wttj,
    "LinkedIn":             fetch_linkedin,
    "YCombinator":          fetch_yc,
    "Adzuna":               fetch_adzuna,
}

AVAILABLE_SOURCES = list(SOURCE_FETCHERS.keys())


def fetch_jobs_for_source(source: str) -> list[dict[str, Any]]:
    """Appelé par app.py à la place de la version mock."""
    fetcher = SOURCE_FETCHERS.get(source)
    if not fetcher:
        print(f"[sources] Source inconnue : {source}")
        return []
    try:
        return fetcher()
    except Exception as e:
        print(f"[sources] Erreur {source}: {e}")
        return []
