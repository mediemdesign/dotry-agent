# KI-Kompass V5 – alle Sessions korrigiert

## Korrigiert
- Abschlussblock auf allen 11 Session-Seiten neu und einheitlich gesetzt.
- Jeder Button hat jetzt zusätzlich ein direktes `onclick="dotryCompleteSession(X)"`.
- Jede Session-Seite hat einen sichtbaren KI-Kompass-Bereich.
- Nach Abschluss springt die Seite automatisch zum Kompass.
- Feedbackbox zeigt freigeschaltete Fähigkeit und aktuellen Stand.

## Test
1. `python -m http.server 8000`
2. `compass-test.html` öffnen und Sessions 1, 2, 3 speichern.
3. `index.html` öffnen: Fortschritt sollte 3/11 anzeigen.
4. Danach `lektion-02.html` oder `lektion-03.html` öffnen und unten abschließen.

## Debug
- `dotryDebugCompass()`
- `dotryCompleteSession(2)`
- `dotryResetCompass()`
