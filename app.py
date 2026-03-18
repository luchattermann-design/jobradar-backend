from flask import Flask, jsonify, request
from flask_cors import CORS
import threading
import time
import os

from greenhouse  import fetch_greenhouse_jobs
from lever       import fetch_lever_jobs
from ashby       import fetch_ashby_jobs
from remoteok    import fetch_remoteok_jobs
from yc          import fetch_yc_jobs
from wttj        import fetch_wttj_jobs
from himalayas   import fetch_himalayas_jobs
from wwr         import fetch_wwr_jobs
from hn          import fetch_hn_jobs
from scorer      import score_job

app = Flask(__name__)
CORS(app)

scan_state = {
    "running":  False,
    "progress": 0,
    "status":   "En attente",
    "jobs":     [],
}

def run_scan(min_score=35, max_jobs=25):
    global scan_state
    scan_state.update({"running": True, "progress": 0, "jobs": []})

    steps = [
        ("Connexion aux sources…",      None),
        ("Scan Greenhouse…",            fetch_greenhouse_jobs),
        ("Scan Lever…",                 fetch_lever_jobs),
        ("Scan Ashby…",                 fetch_ashby_jobs),
        ("Scan RemoteOK…",              fetch_remoteok_jobs),
        ("Scan YCombinator…",           fetch_yc_jobs),
        ("Scan Welcome to the Jungle…", fetch_wttj_jobs),
        ("Scan Himalayas…",             fetch_himalayas_jobs),
        ("Scan We Work Remotely…",      fetch_wwr_jobs),
        ("Scan Hacker News Hiring…",    fetch_hn_jobs),
        ("Calcul des scores…",          None),
        ("Filtrage et tri…",            None),
    ]

    all_jobs = []
    total = len(steps)

    for i, (label, fetcher) in enumerate(steps):
        scan_state["status"]   = label
        scan_state["progress"] = int((i / total) * 100)
        if fetcher:
            try:
                jobs = fetcher()
                all_jobs.extend(jobs)
            except Exception as e:
                print(f"Erreur {label}: {e}")
        time.sleep(0.2)

    scored = []
    seen_links = set()
    for job in sorted(all_jobs, key=lambda j: score_job(j), reverse=True):
        if len(scored) >= max_jobs:
            break
        score = score_job(job)
        if score < min_score:
            continue
        link = job.get("link", "")
        if not link or link in seen_links:
            continue
        seen_links.add(link)
        scored.append({
            "company":  job.get("company", ""),
            "position": job.get("position", ""),
            "location": job.get("location", ""),
            "link":     link,
            "source":   job.get("source", ""),
            "score":    score,
        })

    scan_state.update({
        "running":  False,
        "progress": 100,
        "status":   f"Terminé — {len(scored)} offres trouvées",
        "jobs":     scored,
    })


@app.route("/")
def index():
    return jsonify({"status": "JobRadar API running"})

@app.route("/health")
def health():
    return jsonify({"ok": True})

@app.route("/scan", methods=["POST"])
def start_scan():
    if scan_state["running"]:
        return jsonify({"error": "Scan deja en cours"}), 409
    data      = request.get_json(silent=True) or {}
    min_score = int(data.get("min_score", 35))
    max_jobs  = int(data.get("max_jobs",  25))
    thread = threading.Thread(target=run_scan, args=(min_score, max_jobs), daemon=True)
    thread.start()
    return jsonify({"message": "Scan demarre"}), 202

@app.route("/status")
def get_status():
    return jsonify({
        "running":  scan_state["running"],
        "progress": scan_state["progress"],
        "status":   scan_state["status"],
        "count":    len(scan_state["jobs"]),
    })

@app.route("/jobs")
def get_jobs():
    return jsonify({"jobs": scan_state["jobs"]})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
