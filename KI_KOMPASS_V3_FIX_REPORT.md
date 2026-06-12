# KI-Kompass V3 – Index-Refresh-Fix

## Was geändert wurde
Die Index-Seite aktualisiert den KI-Kompass jetzt zuverlässiger nach abgeschlossenen Sessions.

Zusätzliche Trigger:
- `pageshow`
- `focus`
- `visibilitychange`
- `storage`
- kurzer Sicherheits-Refresh alle 1,2 Sekunden, nur wenn sich der gespeicherte Stand geändert hat

## Test lokal
1. `python -m http.server 8000`
2. `http://localhost:8000/index.html` öffnen.
3. Session öffnen, z. B. `lektion-01.html`.
4. Unten `Session als erledigt markieren` klicken.
5. Zurück auf `index.html`.
6. Kompass sollte aktualisiert sein.

## Debug in der Browser-Konsole
Stand anzeigen:
`dotryDebugCompass()`

Zurücksetzen:
`dotryResetCompass()`

## Wichtig
Bitte lokal nicht per Doppelklick `file://...` testen, sondern über `http://localhost:8000/`.
