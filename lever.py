import requests

LEVER_COMPANIES = ["applydigital", "deliveroo", "monzo", "wise"]

def fetch_lever_jobs():
    all_jobs = []
    for company in LEVER_COMPANIES:
        url = f"https://api.lever.co/v0/postings/{company}?mode=json"
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"Erreur Lever pour {company}: {e}")
            continue
        jobs = []
        for job in data:
            categories = job.get("categories", {})
            jobs.append({
                "company":     company.capitalize(),
                "position":    job.get("text", ""),
                "location":    categories.get("location", ""),
                "link":        job.get("hostedUrl", ""),
                "source":      "Lever",
                "description": job.get("text", ""),
            })
        print(f"lever/{company}: {len(jobs)} offre(s)")
        all_jobs.extend(jobs)
    return all_jobs
