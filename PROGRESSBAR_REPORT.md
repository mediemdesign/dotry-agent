# Progress-Bar für Sessions

## Umgesetzt
- Alle `lektion-XX.html`-Seiten bekommen einen blauen Scroll-Fortschrittsbalken.
- Der Balken sitzt fix unter dem Header.
- Die Breite aktualisiert sich beim Scrollen und Resize.
- Die Startseite `index.html` enthält den zuletzt korrigierten Newsletter-Fix.

## Technisch
- CSS-Klassen: `.progress-bar`, `.progress-fill`
- Element: `<div id="progress">`
- JavaScript aktualisiert die Breite anhand des Scrollfortschritts.

## Hinweis
Falls eine Session-Seite bereits eine Progress-Bar hatte, wird sie nicht doppelt eingebaut.
