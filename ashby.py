import requests

ASHBY_COMPANIES = ["ramp", "replit", "openai", "airtable", "notion", "linear", "retool"]

def fetch_ashby_jobs():
    all_jobs = []
    for company in ASHBY_COMPANIES:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{company}"
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"Erreur Ashby pour {company}: {e}")
            continue
        jobs = []
        for job in data.get("jobs", []):
            jobs.append({
                "company":     company.capitalize(),
                "position":    job.get("title", ""),
                "location":    job.get("location", ""),
                "link":        job.get("jobUrl", ""),
                "source":      "Ashby",
                "description": job.get("title", ""),
            })
        print(f"ashby/{company}: {len(jobs)} offre(s)")
        all_jobs.extend(jobs)
    return all_jobs
