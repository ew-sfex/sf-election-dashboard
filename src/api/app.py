# src/api/app.py

from flask import Flask, send_file, jsonify
from flask_cors import CORS  # Add this line
from pathlib import Path
import os
import time
import xml.etree.ElementTree as ET

app = Flask(__name__)
CORS(app)

# Configure paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data_generator"

def get_latest_results():
    """
    Simulate election night progression based on current time
    Returns appropriate XML file based on time of day
    """
    # For testing, use time to determine which file to serve
    # In production, this would be based on actual election data
    test_files = sorted([f for f in os.listdir(DATA_DIR) if f.startswith("test_results_")])
    
    # Simple time-based progression (for testing)
    hour = time.localtime().tm_hour
    minute = time.localtime().tm_min
    
    # Calculate progression (0-100%)
    if hour < 20:  # Before 8 PM
        return test_files[0]  # 0% reporting
    elif hour == 20:  # 8 PM
        index = min(minute // 15, len(test_files) - 1)  # Progress every 15 minutes
        return test_files[index]
    else:  # After 8 PM
        return test_files[-1]  # 100% reporting

@app.route('/api/results/latest')
def latest_results():
    """Serve the latest results XML"""
    try:
        filename = get_latest_results()
        return send_file(DATA_DIR / filename, mimetype='application/xml')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/results/<percentage>')
def results_by_percentage(percentage):
    """Serve specific results file by percentage"""
    try:
        filename = f"test_results_{int(percentage):03d}.xml"
        return send_file(DATA_DIR / filename, mimetype='application/xml')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/status')
def api_status():
    """API status and available endpoints"""
    test_files = sorted([f for f in os.listdir(DATA_DIR) if f.startswith("test_results_")])
    return jsonify({
        "status": "online",
        "available_files": test_files,
        "endpoints": {
            "latest_results": "/api/results/latest",
            "results_by_percentage": "/api/results/<percentage>",
            "status": "/api/status"
        }
    })

if __name__ == '__main__':
    app.run(debug=True, port=5001)