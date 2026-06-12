# Sichtbarkeits-Fix Progress-Bar

Die Session-Seiten verwenden jetzt einen eigenen Fortschrittsbalken mit eindeutigen Klassen:
- `.dotry-scroll-progress`
- `.dotry-scroll-progress-fill`

Grund: Einige Session-Seiten hatten bereits eigene `.progress-bar`-CSS-Regeln oder Sticky-Header-Varianten. Der neue Balken nutzt `z-index: 9999`, feste Position unter dem Header und kollidiert nicht mit alten Styles.

Gepatchte Seiten:
- lektion-01.html
- lektion-02.html
- lektion-03.html
- lektion-04.html
- lektion-05.html
- lektion-06.html
- lektion-07.html
- lektion-08.html
- lektion-09.html
- lektion-10.html
- lektion-11.html
