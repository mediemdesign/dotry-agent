# KI-Kompass V2

## Verbesserungen
- Aktualisierung nach Klick auf `Session als erledigt markieren` robuster gemacht.
- Kompass, Header-Chip und Energie werden direkt neu gerendert.
- Nach Abschluss springt die Seite automatisch zum KI-Kompass.
- Erfolgsfeedback zeigt freigeschaltete Fähigkeit, Level und Session-Fortschritt.
- `pageshow` aktualisiert den Kompass auch beim Zurück-Navigieren im Browser.
- Debug-Funktion in Console:
  `dotryResetCompass()`

## Test
1. `python -m http.server 8000`
2. `http://localhost:8000/lektion-01.html`
3. Unten auf `Session als erledigt markieren` klicken.
4. Seite springt zum KI-Kompass.
5. Fähigkeit und Zähler aktualisieren sich.
6. Zurück zu `index.html` – Stand bleibt gespeichert.
