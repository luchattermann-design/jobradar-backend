import requests
import xml.etree.ElementTree as ET

# WWR a des flux RSS par catégorie
WWR_FEEDS = {
    "business":   "https://weworkremotely.com/categories/remote-business-exec-management-jobs.rss",
    "sales":      "https://weworkremotely.com/categories/remote-sales-jobs.rss",
    "marketing":  "https://weworkremotely.com/categories/remote-marketing-jobs.rss",
    "all_others": "https://weworkremotely.com/categories/remote-all-other-jobs.rss",
}

RELEVANT_KEYWORDS = [
    "customer success",
    "account manager",
    "account executive",
    "business development",
    "partnerships",
    "client",
    "growth",
    "csm",
    "relationship",
    "sales",
]

def fetch_wwr_jobs():
    all_jobs = []
    headers = {"User-Agent": "Mozilla/5.0"}

    for category, url in WWR_FEEDS.items():
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            root = ET.fromstring(response.content)
        except Exception as e:
            print(f"Erreur WWR ({category}): {e}")
            continue

        channel = root.find("channel")
        if channel is None:
            continue

        items = channel.findall("item")
        found = 0

        for item in items:
            title   = item.findtext("title", "").strip()
            link    = item.findtext("link", "").strip()
            company_region = title  # WWR formate "Company: Title | Region"
            desc    = item.findtext("description", "").strip()

            # Filtre sur titre + description
            combined = (title + " " + desc).lower()
            if not any(kw in combined for kw in RELEVANT_KEYWORDS):
                continue

            # Parse "Company Name: Job Title" ou "Job Title at Company"
            if ": " in title:
                parts   = title.split(": ", 1)
                company = parts[0].strip()
                position = parts[1].strip()
            else:
                company  = "Unknown"
                position = title

            all_jobs.append({
                "company":     company,
                "position":    position,
                "location":    "Remote",
                "link":        link,
                "source":      "WeWorkRemotely",
                "description": desc[:500] if desc else title,
            })
            found += 1

        print(f"wwr/{category}: {found} offre(s) pertinente(s) trouvée(s)")

    # Dédoublonnage
    seen = set()
    unique = []
    for job in all_jobs:
        if job["link"] not in seen:
            seen.add(job["link"])
            unique.append(job)

    return unique
