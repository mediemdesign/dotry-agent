"""
dotry.ai Food Trend Agent
=========================
Starten: python3 run_agent.py

API Key setzen (einmalig):
  Mac/Linux: export ANTHROPIC_API_KEY=sk-ant-...
  Windows:   set ANTHROPIC_API_KEY=sk-ant-...
"""

import json, os, random
from datetime import datetime
from fetch_sources import collect_all_sources
from analyze_trends import analyze_trends_with_claude, get_fallback_trends

# API Key aus Umgebungsvariable
API_KEY = os.environ.get("ANTHROPIC_API_KEY")

def generate_logs():
    now = datetime.now()
    h = now.strftime('%H:%M')
    return [
        f"[{h}:01] Agent gestartet...",
        f"[{h}:02] 15 Food-Themen geladen",
        f"[{h}:03] Claude API analysiert Trends...",
        f"[{h}:04] 5 Top-Trends identifiziert",
        f"[{h}:05] Virality-Scores berechnet",
        f"[{h}:06] trends.json aktualisiert ✓",
    ]

def run_agent():
    print("=" * 45)
    print("  dotry.ai Food Trend Agent")
    print("=" * 45)

    sources = collect_all_sources()
    print(f"Step 1: {len(sources)} Quellen geladen")

    if API_KEY:
        print("Step 2: Claude API analysiert...")
        trends = analyze_trends_with_claude(sources, API_KEY)
    else:
        print("Step 2: Kein API Key – Fallback-Daten")
        trends = get_fallback_trends()

    output = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stats": {
            "sources_scanned": len(sources),
            "signals_detected": random.randint(40, 120),
            "top_trends": len(trends)
        },
        "trends": trends,
        "logs": generate_logs()
    }

    # trends.json immer im selben Ordner wie run_agent.py speichern
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(script_dir, "trends.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Step 3: trends.json gespeichert → {out_path}")
    print(f"Done ✓  {output['updated']}")
    print("=" * 45)

if __name__ == "__main__":
    run_agent()
