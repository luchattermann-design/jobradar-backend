import requests

GREENHOUSE_COMPANIES = ["typeform", "gitlab", "remote", "notion", "figma", "intercom", "zendesk"]

def fetch_greenhouse_jobs():
    all_jobs = []
    for company in GREENHOUSE_COMPANIES:
        url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"Erreur Greenhouse pour {company}: {e}")
            continue
        jobs = []
        for job in data.get("jobs", []):
            jobs.append({
                "company":     company.capitalize(),
                "position":    job.get("title", ""),
                "location":    job.get("location", {}).get("name", ""),
                "link":        job.get("absolute_url", ""),
                "source":      "Greenhouse",
                "description": job.get("title", ""),
            })
        print(f"greenhouse/{company}: {len(jobs)} offre(s)")
        all_jobs.extend(jobs)
    return all_jobs
