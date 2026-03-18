import requests

HIMALAYAS_URL = "https://himalayas.app/jobs/api"

# Paramètres de filtre (optionnels, Himalayas supporte les query params)
HIMALAYAS_PARAMS = {
    "limit": 100,
}

RELEVANT_CATEGORIES = [
    "customer success",
    "account management",
    "sales",
    "business development",
    "partnerships",
    "growth",
    "account executive",
    "client",
    "relationship",
]

def fetch_himalayas_jobs():
    try:
        response = requests.get(
            HIMALAYAS_URL,
            params=HIMALAYAS_PARAMS,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Erreur Himalayas: {e}")
        return []

    jobs_raw = data.get("jobs", [])
    jobs = []

    for job in jobs_raw:
        title = job.get("title", "").lower()
        category = job.get("categories", [])
        category_str = " ".join(category).lower() if isinstance(category, list) else str(category).lower()

        # Filtre léger côté client pour ne garder que les postes pertinents
        combined = title + " " + category_str
        if not any(kw in combined for kw in RELEVANT_CATEGORIES):
            continue

        # Localisation : Himalayas est remote-first
        location = job.get("locationRestrictions", [])
        if isinstance(location, list) and location:
            location_str = ", ".join(location)
        else:
            location_str = "Remote"

        jobs.append({
            "company":     job.get("companyName", "Unknown"),
            "position":    job.get("title", ""),
            "location":    location_str,
            "link":        f"https://himalayas.app/jobs/{job.get('slug', '')}",
            "source":      "Himalayas",
            "description": job.get("description", "") or job.get("title", ""),
        })

    print(f"himalayas: {len(jobs)} offre(s) pertinente(s) trouvée(s)")
    return jobs
