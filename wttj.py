import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

WTTJ_KEYWORDS  = ["customer success", "account manager", "business development"]
WTTJ_LOCATIONS = ["barcelona", "paris", "amsterdam", "remote"]

def fetch_wttj_jobs():
    headers = {"User-Agent": "Mozilla/5.0"}
    jobs = []
    for keyword in WTTJ_KEYWORDS:
        for location in WTTJ_LOCATIONS:
            url = f"https://www.welcometothejungle.com/en/jobs?query={quote(keyword)}&aroundQuery={quote(location)}"
            try:
                response = requests.get(url, headers=headers, timeout=20)
                response.raise_for_status()
            except Exception as e:
                print(f"Erreur WTTJ {keyword}/{location}: {e}")
                continue
            soup = BeautifulSoup(response.text, "html.parser")
            found = 0
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                text = link.get_text(" ", strip=True)
                if "/jobs/" not in href or not text or len(text) < 8:
                    continue
                full_link = href if href.startswith("http") else f"https://www.welcometothejungle.com{href}"
                jobs.append({
                    "company":     "WTTJ",
                    "position":    text[:120],
                    "location":    location,
                    "link":        full_link,
                    "source":      "WTTJ",
                    "description": text,
                })
                found += 1
            print(f"wttj/{keyword}/{location}: {found} offre(s)")
    seen, unique = set(), []
    for job in jobs:
        key = job["link"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique
