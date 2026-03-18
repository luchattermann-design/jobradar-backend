import requests
import re
from datetime import datetime

HN_API = "https://hacker-news.firebaseio.com/v0"

RELEVANT_KEYWORDS = [
    "customer success",
    "account manager",
    "account executive",
    "business development",
    "partnerships",
    "csm",
    "client success",
    "growth",
    "sales",
    "relationship manager",
    "post-sales",
]

LOCATION_KEYWORDS = [
    "switzerland", "suisse", "zurich", "zürich", "geneva", "genève",
    "germany", "berlin", "munich", "frankfurt",
    "netherlands", "amsterdam",
    "france", "paris",
    "spain", "barcelona", "madrid",
    "remote", "eu", "europe", "emea",
]

def get_current_hiring_thread():
    """Trouve le thread 'Ask HN: Who is hiring?' du mois en cours."""
    try:
        # Cherche dans les stories récentes de whoishiring (user officiel HN)
        url = f"{HN_API}/user/whoishiring.json"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        submitted = data.get("submitted", [])
        # Le plus récent est le premier
        return submitted[0] if submitted else None
    except Exception as e:
        print(f"Erreur HN thread search: {e}")
        return None

def fetch_hn_jobs():
    thread_id = get_current_hiring_thread()
    if not thread_id:
        print("hn: impossible de trouver le thread Who's Hiring")
        return []

    try:
        thread = requests.get(f"{HN_API}/item/{thread_id}.json", timeout=10).json()
        month = datetime.fromtimestamp(thread.get("time", 0)).strftime("%B %Y")
        print(f"hn: thread trouvé — Ask HN: Who is hiring? ({month})")
    except Exception as e:
        print(f"Erreur HN thread fetch: {e}")
        return []

    kids = thread.get("kids", [])[:300]  # On limite à 300 commentaires
    jobs = []
    errors = 0

    for kid_id in kids:
        try:
            item = requests.get(f"{HN_API}/item/{kid_id}.json", timeout=8).json()
        except Exception:
            errors += 1
            continue

        if not item or item.get("deleted") or item.get("dead"):
            continue

        text = item.get("text", "") or ""
        text_clean = re.sub(r"<[^>]+>", " ", text)   # retire le HTML
        text_lower = text_clean.lower()

        # Filtre : doit mentionner un rôle pertinent
        if not any(kw in text_lower for kw in RELEVANT_KEYWORDS):
            continue

        # Filtre optionnel : localisation
        has_location = any(loc in text_lower for loc in LOCATION_KEYWORDS)
        if not has_location:
            continue

        # Extrait le titre et l'entreprise depuis les premières lignes
        lines = [l.strip() for l in text_clean.split("|") if l.strip()]
        company  = lines[0][:80]  if lines else "HN Company"
        position = lines[1][:120] if len(lines) > 1 else "See post"

        # Lien vers le commentaire HN
        link = f"https://news.ycombinator.com/item?id={kid_id}"

        jobs.append({
            "company":     company,
            "position":    position,
            "location":    "Remote / Various",
            "link":        link,
            "source":      "HackerNews",
            "description": text_clean[:600],
        })

    print(f"hn: {len(jobs)} offre(s) pertinente(s) ({errors} erreurs réseau ignorées)")
    return jobs
