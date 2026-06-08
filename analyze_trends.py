import json
import urllib.request
import urllib.error

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"

def analyze_trends_with_claude(raw_sources, api_key):
    topics_list = "\n".join(f"- {t}" for t in raw_sources)

    prompt = f"""Du bist ein Food Trend Scout für TikTok, Instagram Reels, YouTube Shorts und Pinterest.

Analysiere die folgenden aktuellen Food-Themen:

{topics_list}

DEINE AUFGABE:

Finde die 5 spannendsten AUFKOMMENDEN Food-Trends.

WICHTIG:

Bewerte Trends NICHT nach ihrer allgemeinen Bekanntheit.

Bewerte stattdessen nach:

Wachstumsgeschwindigkeit auf Social Media
Viralität der letzten 30 Tage
Wahrscheinlichkeit, in den nächsten 60 Tagen weiter zu wachsen
Visuelle Attraktivität für Reels und TikTok
Neuheitswert

Priorisiere:

neue Food-Konzepte
ungewöhnliche Geschmackskombinationen
innovative Rezeptideen
auffällige Präsentationen
internationale Trends, die gerade global werden
Gerichte mit starkem "Wow-Effekt"

Vermeide:

dauerhaft etablierte Trends
generische Fitness-Foods
klassische Meal-Prep-Inhalte
Standard-Burger
allgemeine Pasta-Trends
offensichtliche Dauerbrenner

Die 5 Trends müssen möglichst unterschiedlich sein.

Nicht mehr als:

1 Dessert
1 Protein/Fitness Trend
1 Asian Trend

Für jeden Trend bewerte zusätzlich:

trend_type:

Emerging
Growing
Peak
Declining

Mindestens 3 Trends müssen Emerging oder Growing sein.

Antworte NUR mit einem JSON Array:

{{
"name": "Trend Name",
"category": "freie Kategorie",
"trend_type": "Emerging",
"score": 88,
"confidence": 90,
"description": "2 Sätze auf Deutsch warum dieser Trend viral wird.",
"why_trending": "max 8 Wörter"
}}

Gib exakt 5 Trends zurück.
Nur JSON.
Keine Erklärungen.
Kein Markdown.
Keine zusätzlichen Texte."""

    body = json.dumps({
        "model": "claude-haiku-4-5",
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        CLAUDE_API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        },
        method="POST"
    )

    try:
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())
        text = data["content"][0]["text"].strip()

        # Clean JSON falls nötig
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        trends = json.loads(text)
        print(f"✅ Claude analyzed {len(trends)} trends successfully")
        return trends

    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"❌ Claude API error: {e.code} - {error_body}")
        return get_fallback_trends()
    except Exception as e:
        print(f"❌ Analysis error: {e}")
        return get_fallback_trends()


def get_fallback_trends():
    print("⚠️  Using fallback trends")
    return [
        {
            "name": "Chili Crisp Everything",
            "category": "Snacks",
            "score": 92,
            "confidence": 88,
            "description": "Chili Crisp als universelles Topping erobert soziale Medien. Von Pasta bis Eis – fast nichts bleibt verschont.",
            "why_trending": "Einfach anzuwenden, visuell spektakulär"
        },
        {
            "name": "High Protein Pasta",
            "category": "Health",
            "score": 88,
            "confidence": 85,
            "description": "Pasta aus Hülsenfrüchten explodiert auf TikTok. Gym-Community trifft Italian-Food-Lovers.",
            "why_trending": "Fitness-Trend trifft Comfort Food"
        },
        {
            "name": "Smash Burger Variations",
            "category": "Comfort Food",
            "score": 85,
            "confidence": 82,
            "description": "Der klassische Smash Burger entwickelt sich weiter – Korean BBQ und Birria als neue Stars.",
            "why_trending": "Unendliche Variationen, einfach nachmachbar"
        },
        {
            "name": "Bento Box Aesthetic",
            "category": "Meal Prep",
            "score": 81,
            "confidence": 79,
            "description": "Japanische Lunchboxen als Content-Format. Ordnung, Farbe und Portionierung dominieren Food-Instagram.",
            "why_trending": "Meal Prep trifft visuellen Content"
        },
        {
            "name": "Dubai Chocolate",
            "category": "Dessert",
            "score": 78,
            "confidence": 90,
            "description": "Pistachio-Tahini gefüllte Schokolade aus Dubai ist der neue virale Dessert-Hit in Europa.",
            "why_trending": "Exotisch, fotogen, nachmachbar"
        }
    ]
