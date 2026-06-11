# dotry.ai SEO/URL-Bereinigung – .html-Version

Diese Version ist wieder konsequent auf statische `.html`-URLs umgestellt.

## Warum
- Funktioniert lokal mit `python -m http.server`
- Funktioniert zuverlässig auf GitHub Pages
- Keine serverseitigen Rewrite-Regeln für Clean URLs nötig

## Konsistente URL-Strategie
- Sessions: `/lektion-01.html` bis `/lektion-11.html`
- Übersicht: `/lektionen.html`
- Agent Dashboard: `/agent_dashboard.html`
- Canonicals, OG-URLs, interne Links und Sitemap verwenden `.html`.

## Nach Upload
1. `https://dotry.ai/sitemap.xml` prüfen.
2. Sitemap in Search Console neu einreichen.
3. URL-Prüfung für `lektion-05.html`, `lektion-07.html`, `lektion-08.html`.
4. Validierung für Umleitungsfehler starten.

## Wichtig
Falls Cloudflare aktuell `.html` automatisch auf Clean URLs ohne `.html` weiterleitet, diese Regel entfernen oder deaktivieren.
