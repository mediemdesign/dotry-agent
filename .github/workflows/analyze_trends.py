import json
import urllib.request
import urllib.error

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"

def analyze_trends_with_claude(raw_sources, api_key):
    topics_list = "\n".join(f"- {t}" for t in raw_sources)

    prompt = f"""Du bist ein Food-Trend Analyst für Social Media. Analysiere diese aktuellen Food-Themen und wähle die 5 interessantesten Trends aus.

Themen:
{topics_list}

Antworte NUR mit einem JSON Array (kein Markdown, keine Erklärung davor oder danach):
[
  {{
    "name": "Trend Name (kurz, max 4 Wörter, auf Deutsch)",
    "category": "eine von: Comfort Food, Health, Asian Fusion, Dessert, Snacks, Meal Prep",
    "score": 85,
    "confidence": 90,
    "description": "2 Sätze auf Deutsch warum dieser Trend gerade auf Instagram und TikTok viral geht.",
    "why_trending": "Ein konkreter Grund in max 8 Wörtern auf Deutsch"
  }}
]

Gib exakt 5 Trends zurück. Nur das JSON Array, absolut nichts anderes."""

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
