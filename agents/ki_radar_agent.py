#!/usr/bin/env python3
"""
dotry.ai – KI-Radar Agent V2
============================
Wöchentlicher KI-Radar-Redaktionsagent für dotry.ai.

V2: stärkerer dotry.ai-Filter, weniger Hype/Drama, mehr praktische Relevanz.

Was der Agent macht:
1. RSS-Quellen aus data/ki-radar-sources.json abrufen
2. aktuelle KI-Trends sammeln
3. mit Anthropic oder OpenAI bewerten, wenn ein API-Key vorhanden ist
4. data/ki-radar.json schreiben
5. ki-radar.html aus templates/ki-radar-template.html erzeugen

GitHub Secrets:
- ANTHROPIC_API_KEY  (empfohlen) oder
- OPENAI_API_KEY

Optional ENV:
- KI_RADAR_MODEL_ANTHROPIC, Standard: claude-3-5-haiku-latest
- KI_RADAR_MODEL_OPENAI, Standard: gpt-4o-mini
- KI_RADAR_MAX_ITEMS, Standard: 24
"""

from __future__ import annotations

import email.utils
import html
import json
import os
import re
import sys
import textwrap
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCES_PATH = ROOT / "data" / "ki-radar-sources.json"
DATA_OUT = ROOT / "data" / "ki-radar.json"
TEMPLATE_PATH = ROOT / "templates" / "ki-radar-template.html"
HTML_OUT = ROOT / "ki-radar.html"
MAX_ITEMS = int(os.getenv("KI_RADAR_MAX_ITEMS", "32"))
LOOKBACK_DAYS = int(os.getenv("KI_RADAR_LOOKBACK_DAYS", "14"))

KEYWORDS = [
    # dotry.ai-Relevanz: praktisch, arbeitsnah, einsteigerfreundlich
    "agent", "agents", "assistant", "automation", "automatisierung", "workflow",
    "productivity", "produktivität", "office", "workspace", "email", "meeting",
    "calendar", "notion", "excel", "sheets", "docs", "copilot",
    "chatgpt", "claude", "gemini", "openai", "anthropic", "google", "microsoft",
    "small business", "smb", "kmu", "self-employed", "selbständig",
    "learn", "learning", "academy", "course", "guide", "tutorial",
    "ai search", "recherche", "knowledge work", "wissensarbeit"
]

# Begriffe, die oft Hype, Drama oder reine Meta-Diskussion signalisieren.
# Diese Meldungen sind nicht automatisch falsch, werden aber stark abgewertet.
LOW_VALUE_PATTERNS = [
    "boycott", "surviving", "survive", "i don't see", "i dont see",
    "disguising", "as a joke", "meme", "drama", "lawsuit", "stock",
    "valuation", "rumor", "leak", "politics", "ban", "reserved for",
    "who will win", "vs google", "is dead", "hot take"
]

HIGH_VALUE_PATTERNS = [
    "academy", "course", "workflow", "agent", "automation", "workspace",
    "copilot", "assistant", "enterprise", "small business", "productivity",
    "meetings", "email", "docs", "sheets", "calendar", "guide", "tutorial"
]

SOURCE_WEIGHTS_HINT = {
    "openai": 4.0,
    "anthropic": 4.0,
    "google": 3.5,
    "microsoft": 3.5,
    "github": 2.2,
    "product hunt": 1.8,
    "hugging": 1.8,
    "reddit": -2.5,
}


SKILLS = ["Kommunikation", "Recherche", "Produktivität", "Kreativität", "Agenten", "Automatisierung"]

@dataclass
class FeedItem:
    title: str
    url: str
    source: str
    summary: str
    published: str | None = None
    weight: float = 1.0


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def fetch_url(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "dotry-ai-ki-radar/1.0 (+https://dotry.ai)",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def strip_tags(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def child_text(node: ET.Element, names: list[str]) -> str:
    for name in names:
        found = node.find(name)
        if found is not None and found.text:
            return strip_tags(found.text)
    # namespace fallback
    for child in list(node):
        tag = child.tag.split("}")[-1].lower()
        if tag in [n.lower().split(":")[-1] for n in names] and child.text:
            return strip_tags(child.text)
    return ""


def child_attr(node: ET.Element, tag_name: str, attr: str) -> str:
    for child in list(node):
        tag = child.tag.split("}")[-1].lower()
        if tag == tag_name.lower():
            return child.attrib.get(attr, "")
    return ""


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    try:
        dt = email.utils.parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value[:25], fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            continue
    return None


def parse_feed(xml_bytes: bytes, source_name: str, weight: float) -> list[FeedItem]:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        print(f"⚠️ Feed konnte nicht gelesen werden: {source_name}: {e}", file=sys.stderr)
        return []

    items: list[FeedItem] = []

    # RSS item
    for item in root.findall(".//item"):
        title = child_text(item, ["title"])
        link = child_text(item, ["link"])
        summary = child_text(item, ["description", "summary", "content"])
        published = child_text(item, ["pubDate", "published", "updated"])
        if title and link:
            items.append(FeedItem(title=title, url=link, source=source_name, summary=summary[:600], published=published, weight=weight))

    # Atom entry
    for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry") + root.findall(".//entry"):
        title = child_text(entry, ["title"])
        link = child_attr(entry, "link", "href") or child_text(entry, ["link"])
        summary = child_text(entry, ["summary", "content"])
        published = child_text(entry, ["published", "updated"])
        if title and link:
            items.append(FeedItem(title=title, url=link, source=source_name, summary=summary[:600], published=published, weight=weight))

    return items


def relevant_score(item: FeedItem) -> float:
    """Heuristische Vorfilterung vor der LLM-Bewertung.

    Ziel: weniger Reddit-Drama und Tool-Hype, mehr praktische dotry.ai-Themen.
    Die finale Entscheidung trifft das LLM, aber diese Sortierung bestimmt,
    welche Kandidaten überhaupt prominent in den Prompt gelangen.
    """
    text = f"{item.title} {item.summary}".lower()
    source = (item.source or "").lower()
    score = item.weight

    for src, bonus in SOURCE_WEIGHTS_HINT.items():
        if src in source:
            score += bonus

    for kw in KEYWORDS:
        if kw in text:
            score += 1.0

    for pattern in HIGH_VALUE_PATTERNS:
        if pattern in text:
            score += 2.0

    for pattern in LOW_VALUE_PATTERNS:
        if pattern in text:
            score -= 4.0

    # Reddit ist als Stimmungsquelle okay, aber nicht als Hauptquelle.
    if "reddit" in source:
        score -= 2.0

    dt = parse_date(item.published)
    if dt:
        days = (now_utc() - dt).days
        if days <= 3:
            score += 2.0
        elif days <= 7:
            score += 1.2
        elif days <= LOOKBACK_DAYS:
            score += 0.5

    return score


def collect_items() -> list[FeedItem]:
    cfg = read_json(SOURCES_PATH)
    all_items: list[FeedItem] = []
    cutoff = now_utc() - timedelta(days=LOOKBACK_DAYS)

    for source in cfg.get("sources", []):
        name = source.get("name", "Quelle")
        url = source.get("url")
        weight = float(source.get("weight", 1.0))
        if not url:
            continue
        try:
            print(f"📡 Lade {name}: {url}")
            xml_bytes = fetch_url(url)
            items = parse_feed(xml_bytes, name, weight)
            for item in items:
                dt = parse_date(item.published)
                if dt and dt < cutoff:
                    continue
                all_items.append(item)
        except urllib.error.HTTPError as e:
            print(f"⚠️ HTTP Fehler bei {name}: {e.code}", file=sys.stderr)
        except urllib.error.URLError as e:
            print(f"⚠️ URL Fehler bei {name}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"⚠️ Fehler bei {name}: {e}", file=sys.stderr)

    # deduplicate by URL/title
    seen: set[str] = set()
    unique: list[FeedItem] = []
    for item in sorted(all_items, key=relevant_score, reverse=True):
        key = re.sub(r"\W+", "", (item.url or item.title).lower())[:120]
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique[:MAX_ITEMS]


def prompt_for_llm(items: list[FeedItem]) -> str:
    payload = [asdict(i) for i in items]
    return f"""
Du bist Chefredakteur und KI-Radar-Redakteur von dotry.ai.

Marke und Haltung von dotry.ai:
- modern, schlicht, praktisch, verständlich
- Information gibt es genug. Orientierung macht den Unterschied.
- Ziel ist nicht KI-News zu sammeln, sondern relevante Entwicklungen einzuordnen.
- dotry.ai hilft Menschen, KI im Alltag, Beruf und in kleinen Unternehmen sinnvoll einzusetzen.

Zielgruppe:
- KI-Einsteiger ohne tiefes technisches Vorwissen
- Selbständige und kleine Unternehmen
- Wissensarbeiter, Eltern, Arbeitnehmer
- Menschen, die konkrete Prompts, Workflows, Agenten oder Automatisierungen nutzen möchten

WICHTIGER FILTER:
Ignoriere oder stufe stark ab:
- Reddit-Drama, Meinungen, Boykott-Aufrufe, Spekulationen
- reine Markt-/Börsen-/Akquisitions-News ohne konkreten Nutzen
- Meme-Projekte, Social-Anxiety-Tools, Gimmicks
- "Tool X wird sterben"-Diskussionen
- reine Entwickler-Infrastruktur, wenn kein Alltag/KMU-Nutzen erkennbar ist

Bevorzuge:
- offizielle Produkt-/Feature-/Learning-News von OpenAI, Anthropic, Google, Microsoft
- konkrete Workflows für E-Mail, Meetings, Recherche, Office, Kalender, Dokumente
- Agenten und Automatisierungen mit nachvollziehbarem Nutzen
- Lerninhalte, Kurse oder Beispiele, die Einsteigern helfen
- Trends, aus denen eine dotry.ai Session entstehen könnte

Bewertung: 1 bis 15 Punkte, bestehend aus:
- Alltagstauglichkeit 1–5: Kann ein normaler Nutzer das zeitnah verstehen oder testen?
- Nutzen für KMU/Selbständige 1–5: Spart es Zeit, verbessert es Kommunikation, Recherche oder Abläufe?
- Session-Potenzial 1–5: Könnte daraus eine konkrete dotry.ai Lektion entstehen?

Regeln für die Auswahl:
- Wähle maximal 5 Trends.
- Genau 3 Trends sollen "Sofort relevant" sein, wenn mindestens 3 gute Kandidaten vorhanden sind.
- 1 bis 2 Trends sollen "Beobachten" sein.
- Reddit darf maximal 1 ausgewählter Trend sein und nur, wenn er wirklich praktisch relevant ist.
- Ein Trend unter 10/15 gehört normalerweise nicht in "Sofort relevant".
- Schreibe klar, ruhig und redaktionell. Kein Hype.
- Formuliere alle Texte auf Deutsch.
- Vermeide generische Sätze wie "könnte relevant sein". Nenne den konkreten Nutzen.

Ordne jeden Trend einer KI-Kompass-Fähigkeit zu:
{", ".join(SKILLS)}

Gib ausschließlich gültiges JSON zurück, ohne Markdown.
Schema:
{{
  "summary": "1 ruhiger Satz zur Woche",
  "trends": [
    {{
      "title": "kurzer deutscher Titel, maximal 70 Zeichen",
      "source": "Quelle",
      "url": "URL",
      "category": "Sofort relevant" oder "Beobachten",
      "skill": "eine der Fähigkeiten",
      "score": 1-15,
      "summary": "1-2 Sätze: Was ist passiert?",
      "why_it_matters": "konkret: Warum ist das für Einsteiger, KMU oder Selbständige relevant?",
      "practical_use": "konkret: Was könnte man nächste Woche damit tun?",
      "session_idea": "präzise mögliche dotry.ai Session-Idee, z. B. 'Der Meeting-Agent'"
    }}
  ],
  "impulse": "ein kurzer, pointierter Impuls der Woche im Stil von dotry.ai"
}}

Quellen:
{json.dumps(payload, ensure_ascii=False, indent=2)}
""".strip()

def call_anthropic(prompt: str) -> str | None:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    model = os.getenv("KI_RADAR_MODEL_ANTHROPIC", "claude-3-5-haiku-latest")
    body = {
        "model": model,
        "max_tokens": 3500,
        "temperature": 0.25,
        "messages": [{"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")


def call_openai(prompt: str) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    model = os.getenv("KI_RADAR_MODEL_OPENAI", "gpt-4o-mini")
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Du gibst ausschließlich gültiges JSON zurück."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.25,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if match:
            return json.loads(match.group(0))
        raise


def postprocess_analysis(data: dict[str, Any]) -> dict[str, Any]:
    """Normalisiert die LLM-Ausgabe und entfernt offensichtliche Low-Value-Treffer."""
    trends = data.get("trends") or []
    cleaned = []
    reddit_count = 0
    for t in trends:
        title = str(t.get("title", ""))
        source = str(t.get("source", ""))
        text = f"{title} {t.get('summary','')} {t.get('why_it_matters','')}".lower()
        if any(p in text for p in LOW_VALUE_PATTERNS) and int(t.get("score", 0) or 0) < 13:
            continue
        if "reddit" in source.lower():
            reddit_count += 1
            if reddit_count > 1:
                continue
        try:
            t["score"] = max(1, min(15, int(t.get("score", 0))))
        except Exception:
            t["score"] = 10
        if t["score"] < 10:
            t["category"] = "Beobachten"
        elif str(t.get("category", "")).lower().startswith("sofort"):
            t["category"] = "Sofort relevant"
        else:
            t["category"] = "Beobachten"
        if t.get("skill") not in SKILLS:
            t["skill"] = "Recherche"
        cleaned.append(t)

    cleaned.sort(key=lambda x: int(x.get("score", 0)), reverse=True)
    relevant = [t for t in cleaned if t.get("category") == "Sofort relevant"][:3]
    watch = [t for t in cleaned if t not in relevant][:2]
    data["trends"] = relevant + watch
    if not data.get("summary"):
        data["summary"] = "Diese Woche zählt vor allem, welche KI-Entwicklungen praktisch nutzbar werden."
    if not data.get("impulse"):
        data["impulse"] = "Orientierung entsteht nicht durch mehr News, sondern durch bessere Einordnung."
    return data


def guess_skill(item: FeedItem) -> str:
    text = f"{item.title} {item.summary}".lower()
    if any(w in text for w in ["agent", "assistant", "codex"]):
        return "Agenten"
    if any(w in text for w in ["automation", "workflow", "automatisierung"]):
        return "Automatisierung"
    if any(w in text for w in ["workspace", "office", "email", "meeting", "calendar", "productivity"]):
        return "Produktivität"
    if any(w in text for w in ["search", "research", "recherche"]):
        return "Recherche"
    if any(w in text for w in ["image", "video", "creative", "design"]):
        return "Kreativität"
    return "Recherche"


def fallback_analysis(items: list[FeedItem]) -> dict[str, Any]:
    # Fallback soll ebenfalls dotry.ai-tauglicher sein als generische News-Ausgabe.
    filtered = [i for i in items if relevant_score(i) >= 4][:5]
    selected = filtered or items[:5]
    trends = []
    for idx, item in enumerate(selected):
        raw_score = int(round(relevant_score(item)))
        score = min(15, max(8, raw_score))
        skill = guess_skill(item)
        title = item.title[:80]
        trends.append({
            "title": title,
            "source": item.source,
            "url": item.url,
            "category": "Sofort relevant" if score >= 11 and idx < 3 else "Beobachten",
            "skill": skill,
            "score": score,
            "summary": item.summary[:220] or "Diese Entwicklung wurde im KI-Radar erfasst.",
            "why_it_matters": f"Relevant, wenn daraus ein einfacher Nutzen rund um {skill.lower()} entsteht – etwa ein besserer Workflow, ein verständlicher Prompt oder eine konkrete Alltagshilfe.",
            "practical_use": "Als Impuls prüfen: Kann daraus eine einfache Schritt-für-Schritt-Anleitung für Alltag, Beruf oder kleine Unternehmen werden?",
            "session_idea": f"Session-Idee: {skill} praktisch im Alltag einsetzen",
        })
    return {
        "summary": "Diese Woche steht praktische KI-Anwendung stärker im Fokus als reine Tool-News.",
        "trends": trends,
        "impulse": "Nicht jede KI-Meldung verdient Aufmerksamkeit. Relevant wird sie erst, wenn sie eine konkrete Aufgabe einfacher macht.",
    }


def analyze(items: list[FeedItem]) -> dict[str, Any]:
    if not items:
        return fallback_analysis([])
    prompt = prompt_for_llm(items)
    try:
        response = call_anthropic(prompt)
        if response:
            return postprocess_analysis(extract_json(response))
    except Exception as e:
        print(f"⚠️ Anthropic Analyse fehlgeschlagen: {e}", file=sys.stderr)
    try:
        response = call_openai(prompt)
        if response:
            return postprocess_analysis(extract_json(response))
    except Exception as e:
        print(f"⚠️ OpenAI Analyse fehlgeschlagen: {e}", file=sys.stderr)
    return postprocess_analysis(fallback_analysis(items))


def esc(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def card(trend: dict[str, Any]) -> str:
    title = esc(trend.get("title"))
    source = esc(trend.get("source"))
    url = esc(trend.get("url"))
    category = esc(trend.get("category"))
    skill = esc(trend.get("skill"))
    score = esc(trend.get("score"))
    summary = esc(trend.get("summary"))
    why = esc(trend.get("why_it_matters"))
    use = esc(trend.get("practical_use"))
    return f"""
      <article class="trend-card">
        <div class="trend-top"><span class="trend-cat">{category}</span><span class="trend-score">{score}/15</span></div>
        <span class="skill">🧭 {skill}</span>
        <h3>{title}</h3>
        <p>{summary}</p>
        <p><strong style="color:var(--text);">Warum relevant:</strong><br>{why}</p>
        <p><strong style="color:var(--text);">Praktischer Nutzen:</strong><br>{use}</p>
        <a href="{url}" target="_blank" rel="noopener">Quelle: {source} →</a>
      </article>
    """.strip()


def render_html(data: dict[str, Any], source_count: int) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    trends = data.get("trends", [])[:5]
    relevant = [t for t in trends if str(t.get("category", "")).lower().startswith("sofort")]
    watch = [t for t in trends if t not in relevant]
    if not relevant and trends:
        relevant = trends[:3]
        watch = trends[3:]
    if not watch:
        watch = trends[3:5] if len(trends) > 3 else trends[:1]

    idea_trend = trends[0] if trends else {}
    session_idea = idea_trend.get("session_idea") or "Session-Idee: Ein aktueller KI-Trend wird in eine praktische dotry.ai Lektion übersetzt."
    idea_html = f"""
      <h3>{esc(session_idea)}</h3>
      <p><strong>Auslöser:</strong> {esc(idea_trend.get('title', 'Aktueller KI-Trend'))}</p>
      <p>{esc(idea_trend.get('practical_use', 'Der Trend wird nach seinem praktischen Nutzen für Alltag, Beruf und Einsteiger bewertet.'))}</p>
    """.strip()

    generated = data.get("generated_at") or now_utc().isoformat()
    try:
        dt = datetime.fromisoformat(generated.replace("Z", "+00:00"))
        date_label = dt.strftime("%d.%m.%Y")
    except Exception:
        date_label = generated[:10]

    replacements = {
        "{{WEEK_LABEL}}": esc(data.get("week_label", "Diese Woche")),
        "{{GENERATED_DATE}}": esc(date_label),
        "{{COUNT_TRENDS}}": str(source_count),
        "{{COUNT_TOP}}": str(len(trends)),
        "{{RELEVANT_CARDS}}": "\n".join(card(t) for t in relevant) or "<p>Diese Woche wurden keine relevanten Trends gefunden.</p>",
        "{{WATCH_CARDS}}": "\n".join(card(t) for t in watch) or "<p>Keine Beobachtungen in dieser Woche.</p>",
        "{{SESSION_IDEA}}": idea_html,
        "{{IMPULSE}}": esc(data.get("impulse", "Information gibt es genug. Orientierung macht den Unterschied.")),
    }
    out = template
    for key, value in replacements.items():
        out = out.replace(key, value)
    return out


def main() -> int:
    print("📡 dotry.ai KI-Radar Agent V2 startet")
    items = collect_items()
    print(f"✅ {len(items)} mögliche Trends gesammelt")

    analysis = analyze(items)
    analysis["generated_at"] = now_utc().isoformat().replace("+00:00", "Z")
    analysis["week_label"] = "Diese Woche"

    write_json(DATA_OUT, analysis)
    html_out = render_html(analysis, source_count=len(items))
    HTML_OUT.write_text(html_out, encoding="utf-8")

    print(f"✅ geschrieben: {DATA_OUT.relative_to(ROOT)}")
    print(f"✅ geschrieben: {HTML_OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
