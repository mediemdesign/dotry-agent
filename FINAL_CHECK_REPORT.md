# Finaler Kurzcheck

## Geprüft
- Keine versehentlichen `session-XX.html`-URLs gefunden.
- Technische URLs bleiben bei `lektion-XX.html`.
- Sitemap ist XML und verwendet `.html`.
- Canonicals der HTML-Seiten sind grundsätzlich konsistent.
- Sichtbare Texte wurden auf „Session/Sessions“ umgestellt.

## Korrigiert
- `agent_dashboard.html` um `robots`, `canonical` und Open-Graph-Basisdaten ergänzt.

## Noch extern sicherstellen
Diese Dateien werden referenziert und müssen ebenfalls im GitHub-Repository liegen:
- `nav.css`
- `logo.png`
- `favicon-32.png`
- `favicon-16.png`
- `apple-touch-icon.png`
- `trends.json`
- `foto_agent_n8n.json` falls Lektion 10 den Download weiterhin anbieten soll

## Hinweis
`nav.html` ist ein Partial und braucht keinen eigenen `<title>`, Canonical oder Robots-Tag.
