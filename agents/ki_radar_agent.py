#!/usr/bin/env python3
"""
dotry.ai – KI-Radar Agent V1
============================
Wöchentlicher Trend-Agent für dotry.ai.

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
MAX_ITEMS = int(os.getenv("KI_RADAR_MAX_ITEMS", "24"))
LOOKBACK_DAYS = int(os.getenv("KI_RADAR_LOOKBACK_DAYS", "14"))

KEYWORDS = [
    "ai", "ki", "agent", "agents", "chatgpt", "claude", "gemini", "copilot",
    "automation", "automatisierung", "workflow", "openai", "anthropic", "google",
    "microsoft", "model", "llm", "assistant", "tools", "productivity"
]

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
    text = f"{item.title} {item.summary}".lower()
    score = item.weight
    for kw in KEYWORDS:
        if kw in text:
            score += 1.0
    dt = parse_date(item.published)
    if dt:
        days = (now_utc() - dt).days
        if days <= 3:
            score += 3
        elif days <= 7:
            score += 2
        elif days <= LOOKBACK_DAYS:
            score += 1
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
Du bist der KI-Radar-Redakteur für dotry.ai.

Zielgruppe:
- KI-Einsteiger
- Arbeitnehmer
- Selbständige
- KMU
- Menschen, die KI praktisch im Alltag nutzen möchten

Aufgabe:
Bewerte die folgenden KI-News NICHT nach Hype, sondern nach praktischer Alltagstauglichkeit.
Wähle maximal 5 Trends aus.

Bewertung: 1 bis 15 Punkte:
- Alltagstauglichkeit 1–5
- Nutzen für KMU/Selbständige 1–5
- Relevanz für KI-Einsteiger 1–5

Ordne jeden Trend einer KI-Kompass-Fähigkeit zu:
{", ".join(SKILLS)}

Gib ausschließlich gültiges JSON zurück, ohne Markdown.
Schema:
{{
  "summary": "1 Satz zur Woche",
  "trends": [
    {{
      "title": "kurzer deutscher Titel",
      "source": "Quelle",
      "url": "URL",
      "category": "Sofort relevant" oder "Beobachten",
      "skill": "eine der Fähigkeiten",
      "score": 1-15,
      "summary": "kurze Zusammenfassung auf Deutsch",
      "why_it_matters": "warum relevant für die Zielgruppe",
      "practical_use": "konkreter praktischer Nutzen",
      "session_idea": "mögliche dotry.ai Session-Idee"
    }}
  ],
  "impulse": "ein kurzer, pointierter Impuls der Woche"
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


def fallback_analysis(items: list[FeedItem]) -> dict[str, Any]:
    selected = items[:5]
    trends = []
    for idx, item in enumerate(selected):
        score = min(15, max(7, int(relevant_score(item))))
        skill = "Agenten" if "agent" in (item.title + item.summary).lower() else "Automatisierung" if "automation" in (item.title + item.summary).lower() else "Recherche"
        trends.append({
            "title": item.title[:90],
            "source": item.source,
            "url": item.url,
            "category": "Sofort relevant" if score >= 11 and idx < 3 else "Beobachten",
            "skill": skill,
            "score": score,
            "summary": item.summary[:220] or "Diese Entwicklung wurde im KI-Radar erfasst und sollte redaktionell geprüft werden.",
            "why_it_matters": "Der Trend könnte für Menschen relevant sein, die KI praktisch im Alltag oder Beruf nutzen möchten.",
            "practical_use": "Prüfen, ob daraus ein konkreter Prompt, Workflow oder eine neue dotry.ai Session entstehen kann.",
            "session_idea": f"Session-Idee: {skill} im Alltag praktisch einsetzen",
        })
    return {
        "summary": "Automatisch gesammelt; ohne LLM-Key wurde eine heuristische Vorauswahl erstellt.",
        "trends": trends,
        "impulse": "Nicht jede neue KI-Meldung ist wichtig. Relevant wird sie erst, wenn sie eine Aufgabe im Alltag einfacher macht.",
    }


def analyze(items: list[FeedItem]) -> dict[str, Any]:
    if not items:
        return fallback_analysis([])
    prompt = prompt_for_llm(items)
    try:
        response = call_anthropic(prompt)
        if response:
            return extract_json(response)
    except Exception as e:
        print(f"⚠️ Anthropic Analyse fehlgeschlagen: {e}", file=sys.stderr)
    try:
        response = call_openai(prompt)
        if response:
            return extract_json(response)
    except Exception as e:
        print(f"⚠️ OpenAI Analyse fehlgeschlagen: {e}", file=sys.stderr)
    return fallback_analysis(items)


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
    print("📡 dotry.ai KI-Radar Agent startet")
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
