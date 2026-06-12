# dotry.ai SEO- und Link-Prüfung

## Umsetzung

- Interne Links konsequent auf Clean URLs ohne `.html` umgestellt.
- Canonical-URLs und `og:url` entsprechend vereinheitlicht.
- Startseite als `index.html` ausgegeben.
- FAQ-Sektion auf der Startseite ergänzt.
- JSON-LD ergänzt: `Organization`, `WebSite`, `FAQPage`, `Course`, `CollectionPage`, `WebPage`.
- `sitemap.xml` und `robots.txt` mit Clean URLs erzeugt.

## Hinweis zur Server-Konfiguration

Damit diese Dateien korrekt funktionieren, muss der Server/Cloudflare Clean URLs bedienen bzw. `.html` dauerhaft per 301 auf die Clean URL weiterleiten.
Beispiel: `/lektion-05.html` → `/session-05`.

## Geprüfte Dateien

- agent_dashboard.html → agent_dashboard.html
- datenschutz.html → datenschutz.html
- impressum.html → impressum.html
- lektion-01.html → lektion-01.html
- lektion-02.html → lektion-02.html
- lektion-03.html → lektion-03.html
- lektion-04.html → lektion-04.html
- lektion-05.html → lektion-05.html
- lektion-06.html → lektion-06.html
- lektion-07.html → lektion-07.html
- lektion-08.html → lektion-08.html
- lektion-09.html → lektion-09.html
- lektion-10.html → lektion-10.html
- lektion-11.html → lektion-11.html
- lektionen.html → lektionen.html
- nav.html → nav.html
- index(3).html → index.html