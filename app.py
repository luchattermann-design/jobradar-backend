from flask import Flask, jsonify, request
from flask_cors import CORS
import threading
import time
import os

from greenhouse import fetch_greenhouse_jobs
from lever import fetch_lever_jobs
from ashby import fetch_ashby_jobs
from remoteok import fetch_remoteok_jobs
from yc import fetch_yc_jobs
from wttj import fetch_wttj_jobs
from himalayas import fetch_himalayas_jobs
from wwr import fetch_wwr_jobs
from hn import fetch_hn_jobs
from scorer import normalize_job, deduplicate_jobs

app = Flask(__name__)

CORS(
    app,
    resources={r"/*": {"origins": "https://luchattermann-design.github.io"}},
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

FETCHERS = {
    "Greenhouse": fetch_greenhouse_jobs,
    "Lever": fetch_lever_jobs,
    "Ashby": fetch_ashby_jobs,
    "RemoteOK": fetch_remoteok_jobs,
    "YCombinator": fetch_yc_jobs,
    "Welcome to the Jungle": fetch_wttj_jobs,
    "Himalayas": fetch_himalayas_jobs,
    "We Work Remotely": fetch_wwr_jobs,
    "Hacker News": fetch_hn_jobs,
}

scan_lock = threading.Lock()
scan_state = {
    "running": False,
    "progress": 0,
    "status": "En attente",
    "jobs": [],
    "count": 0,
    "sources": list(FETCHERS.keys()),
}


def update_scan_state(**kwargs):
    with scan_lock:
        scan_state.update(kwargs)


def run_scan(selected_sources=None):
    sources = selected_sources or list(FETCHERS.keys())

    update_scan_state(
        running=True,
        progress=0,
        status="Initialisation du scan...",
        jobs=[],
        count=0,
        sources=sources,
    )

    all_jobs = []
    total_steps = max(len(sources) + 2, 1)

    try:
        for i, source_name in enumerate(sources):
            fetcher = FETCHERS.get(source_name)
            if not fetcher:
                continue

            update_scan_state(
                status=f"Scan {source_name}...",
                progress=int((i / total_steps) * 100),
            )

            try:
                jobs = fetcher() or []
                normalized = [normalize_job(job, default_source=source_name) for job in jobs]
                all_jobs.extend(normalized)
                update_scan_state(count=len(all_jobs))
            except Exception as e:
                print(f"Erreur {source_name}: {e}")

            time.sleep(0.2)

        update_scan_state(
            status="Dedoublonnage...",
            progress=int((len(sources) / total_steps) * 100),
        )
        deduped = deduplicate_jobs(all_jobs)

        update_scan_state(
            running=False,
            progress=100,
            status=f"Termine - {len(deduped)} offres collectees",
            jobs=deduped,
            count=len(deduped),
        )

    except Exception as e:
        print(f"Erreur globale pendant le scan: {e}")
        update_scan_state(
            running=False,
            progress=100,
            status="Erreur pendant le scan",
            jobs=[],
            count=0,
        )


@app.route("/")
def index():
    return jsonify({"status": "JobRadar API running"})


@app.route("/health")
def health():
    return jsonify({"ok": True})


@app.route("/scan", methods=["POST"])
def start_scan():
    with scan_lock:
        if scan_state["running"]:
            return jsonify({"error": "Scan deja en cours"}), 409

    data = request.get_json(silent=True) or {}
    sources = data.get("sources") or list(FETCHERS.keys())

    thread = threading.Thread(
        target=run_scan,
        args=(sources,),
        daemon=True,
    )
    thread.start()

    return jsonify({"message": "Scan demarre"}), 202


@app.route("/status")
def get_status():
    with scan_lock:
        return jsonify({
            "running": scan_state["running"],
            "progress": scan_state["progress"],
            "status": scan_state["status"],
            "count": scan_state["count"],
            "sources": scan_state["sources"],
        })


@app.route("/jobs")
def get_jobs():
    with scan_lock:
        return jsonify({"jobs": scan_state["jobs"]})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
