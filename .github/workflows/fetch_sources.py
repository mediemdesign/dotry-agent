"""
fetch_sources.py
Sammelt Food-Trend Daten aus öffentlichen Quellen.
Da Reddit/Instagram externe APIs blockieren, nutzen wir
Claude API direkt als intelligente Datenquelle.
"""

# Kuratierte Seed-Begriffe als Basis für die KI-Analyse
FOOD_SEED_TOPICS = [
    "viral pasta recipes TikTok 2026",
    "high protein meal prep trending",
    "smash burger variations viral",
    "Korean street food trends",
    "Mediterranean diet recipes viral",
    "cottage cheese recipes trending",
    "Dubai chocolate viral",
    "pickle flavored foods trending",
    "birria tacos popularity",
    "cloud bread viral recipe",
    "frozen honey TikTok trend",
    "bento box lunch aesthetic",
    "air fryer recipes trending",
    "sourdough discard recipes",
    "chili crisp everything trend",
]

def collect_all_sources():
    """Gibt kuratierte Seed-Topics zurück die Claude analysieren soll."""
    print(f"Sources prepared: {len(FOOD_SEED_TOPICS)} topics")
    return FOOD_SEED_TOPICS
