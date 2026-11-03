from datetime import datetime
from pathlib import Path
import os
import time
import urllib.request
from flask import Flask, jsonify, request, Response, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data_generator"

LIVE_SF_XML_URL = os.environ.get(
    "SF_ELECTION_XML_URL",
    "https://sfelections.org/results/20261103/data/summary.xml",
)
CACHE_TTL_SECONDS = int(os.environ.get("SF_CACHE_TTL_SECONDS", "15"))

_live_cache: dict[str, object] = {
    "fetched_at": 0.0,
    "xml_bytes": b"",
}


def fetch_live_sf_xml() -> bytes:
    now = time.time()
    cached_at = float(_live_cache.get("fetched_at") or 0.0)
    cached_bytes = _live_cache.get("xml_bytes")
    if isinstance(cached_bytes, bytes) and cached_bytes and (now - cached_at) < CACHE_TTL_SECONDS:
        return cached_bytes

    req = urllib.request.Request(
        LIVE_SF_XML_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept": "application/xml,text/xml,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = resp.read()
        _live_cache["fetched_at"] = now
        _live_cache["xml_bytes"] = payload
        return payload


def get_simulated_snapshot_filename() -> str:
    test_files = sorted(
        f for f in os.listdir(DATA_DIR) if f.startswith("test_results_") and f.endswith(".xml")
    )
    if not test_files:
        raise FileNotFoundError(f"No test_results_*.xml files found in {DATA_DIR}")

    hour = time.localtime().tm_hour
    minute = time.localtime().tm_min

    if hour < 20:
        return test_files[0]
    if hour == 20:
        index = min(minute // 15, len(test_files) - 1)
        return test_files[index]
    return test_files[-1]


@app.route("/api/results/live")
def live_results() -> Response:
    """Proxy the official 2026 San Francisco Department of Elections XML with CORS headers."""
    try:
        xml_bytes = fetch_live_sf_xml()
        return Response(
            xml_bytes,
            mimetype="application/xml",
            headers={"Cache-Control": f"public, max-age={CACHE_TTL_SECONDS}"},
        )
    except Exception:
        fallback_path = DATA_DIR / "test_results_000.xml"
        if fallback_path.exists():
            return send_file(fallback_path, mimetype="application/xml")
        return jsonify({"error": "Unable to reach sfelections.org live feed"}), 502


@app.route("/api/results/latest")
def latest_results() -> Response:
    """
    Serve the live 2026 feed by default, or a simulated snapshot when ?mode=sim
    or ?demo=<0|25|50|75|100> is passed.
    """
    demo = request.args.get("demo")
    mode = request.args.get("mode")

    if demo is not None:
        return results_by_percentage(demo)

    if mode == "sim":
        try:
            filename = get_simulated_snapshot_filename()
            return send_file(DATA_DIR / filename, mimetype="application/xml")
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    return live_results()


@app.route("/api/results/<percentage>")
def results_by_percentage(percentage: str) -> Response:
    """Serve a specific simulated 2026 results file by reporting percentage (0, 25, 50, 75, 100)."""
    try:
        pct_int = int(percentage)
        filename = f"test_results_{pct_int:03d}.xml"
        filepath = DATA_DIR / filename
        if not filepath.exists():
            return jsonify({"error": f"Snapshot {filename} not found"}), 404
        return send_file(filepath, mimetype="application/xml")
    except ValueError:
        return jsonify({"error": "Percentage must be an integer (0, 25, 50, 75, 100)"}), 400


@app.route("/api/status")
def api_status() -> Response:
    test_files = sorted(
        f for f in os.listdir(DATA_DIR) if f.startswith("test_results_") and f.endswith(".xml")
    )
    return jsonify(
        {
            "status": "online",
            "election_date": "2026-11-03",
            "upstream_url": LIVE_SF_XML_URL,
            "available_snapshots": test_files,
            "server_time_utc": datetime.utcnow().isoformat() + "Z",
            "endpoints": {
                "live_results": "/api/results/live",
                "latest_results": "/api/results/latest",
                "simulated_by_percentage": "/api/results/<0|25|50|75|100>",
                "status": "/api/status",
            },
        }
    )


if __name__ == "__main__":
    app.run(debug=False, port=5001)
