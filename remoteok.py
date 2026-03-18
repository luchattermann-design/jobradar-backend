import requests

def fetch_remoteok_jobs():
    url = "https://remoteok.com/api"
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Erreur RemoteOK: {e}")
        return []
    jobs = []
    for job in data[1:]:
        tags = job.get("tags", [])
        jobs.append({
            "company":     job.get("company", "RemoteOK"),
            "position":    job.get("position", ""),
            "location":    job.get("location", "Remote"),
            "link":        job.get("url", ""),
            "source":      "RemoteOK",
            "description": job.get("description", "") or str(tags),
        })
    print(f"remoteok: {len(jobs)} offre(s)")
    return jobs
