#!/usr/bin/env python3
"""
dotry.ai – Lektion 10: iPhone Foto-Sortierer
=============================================
Sortiert Fotos automatisch nach Aufnahmedatum und Ort.

Struktur des Zielordners:
  Fotos/
  ├── 2026-05 – Wien/
  │   ├── IMG_001.jpg
  │   └── IMG_002.jpg
  ├── 2026-06 – Kreta/
  │   └── IMG_003.jpg
  └── 2026-06 – Unbekannt/
      └── IMG_004.jpg

Benötigte Pakete:
  pip install Pillow piexif requests

Starten:
  python3 foto_sortierer.py
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

# Pillow für EXIF-Daten
try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
except ImportError:
    print("❌ Pillow nicht installiert.")
    print("   Bitte ausführen: pip install Pillow")
    exit(1)

try:
    import requests
except ImportError:
    print("❌ requests nicht installiert.")
    print("   Bitte ausführen: pip install requests")
    exit(1)


# ─────────────────────────────────────────
# EINSTELLUNGEN – hier anpassen
# ─────────────────────────────────────────

# Ordner mit deinen iPhone Fotos (Quelle)
QUELL_ORDNER = os.path.expanduser("~/Desktop/iPhone_Fotos")

# Ordner wo die sortierten Fotos hinkommen (Ziel)
ZIEL_ORDNER = os.path.expanduser("~/Desktop/Fotos_Sortiert")

# Unterstützte Dateitypen
FOTO_TYPEN = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".tiff", ".tif"}

# GPS-Auflösung: True = Ortsname via Internet abrufen, False = nur Koordinaten
ORT_ABRUFEN = True

# Duplikate überspringen (True empfohlen)
DUPLIKATE_UEBERSPRINGEN = True


# ─────────────────────────────────────────
# HILFSFUNKTIONEN
# ─────────────────────────────────────────

def get_exif_data(bild_pfad):
    """EXIF-Daten aus einem Foto auslesen."""
    try:
        img = Image.open(bild_pfad)
        exif_raw = img._getexif()
        if not exif_raw:
            return {}
        return {TAGS.get(tag, tag): wert for tag, wert in exif_raw.items()}
    except Exception:
        return {}


def get_gps_koordinaten(exif_data):
    """GPS-Koordinaten aus EXIF-Daten extrahieren."""
    gps_info = exif_data.get("GPSInfo")
    if not gps_info:
        return None

    try:
        gps = {GPSTAGS.get(t, t): gps_info[t] for t in gps_info}

        def dms_to_dezimal(dms, ref):
            grad = float(dms[0])
            minuten = float(dms[1])
            sekunden = float(dms[2])
            dezimal = grad + (minuten / 60.0) + (sekunden / 3600.0)
            if ref in ['S', 'W']:
                dezimal = -dezimal
            return dezimal

        lat = dms_to_dezimal(gps['GPSLatitude'], gps['GPSLatitudeRef'])
        lon = dms_to_dezimal(gps['GPSLongitude'], gps['GPSLongitudeRef'])
        return lat, lon
    except Exception:
        return None


def koordinaten_zu_ort(lat, lon):
    """GPS-Koordinaten in Ortsname umwandeln (OpenStreetMap – kostenlos)."""
    try:
        url = f"https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "zoom": 10,
            "accept-language": "de"
        }
        headers = {"User-Agent": "dotry-ai-foto-sortierer/1.0"}
        resp = requests.get(url, params=params, headers=headers, timeout=5)
        data = resp.json()

        address = data.get("address", {})
        # Priorisierung: Stadt > Gemeinde > Bundesland > Land
        ort = (
            address.get("city") or
            address.get("town") or
            address.get("village") or
            address.get("municipality") or
            address.get("state") or
            address.get("country") or
            "Unbekannt"
        )
        return ort
    except Exception:
        return "Unbekannt"


def get_aufnahmedatum(exif_data, datei_pfad):
    """Aufnahmedatum aus EXIF oder Dateiname extrahieren."""
    # Zuerst EXIF DateTimeOriginal
    datum_str = exif_data.get("DateTimeOriginal") or exif_data.get("DateTime")
    if datum_str:
        try:
            return datetime.strptime(datum_str, "%Y:%m:%d %H:%M:%S")
        except Exception:
            pass

    # Fallback: Änderungsdatum der Datei
    ts = os.path.getmtime(datei_pfad)
    return datetime.fromtimestamp(ts)


def ordner_name(datum, ort):
    """Erstellt den Ordnernamen: '2026-05 – Wien'"""
    monat = datum.strftime("%Y-%m")
    # Ungültige Zeichen für Ordnernamen entfernen
    ort_clean = "".join(c for c in ort if c not in r'\/:*?"<>|')
    return f"{monat} – {ort_clean}"


def foto_hash(datei_pfad):
    """Einfacher Hash für Duplikat-Erkennung (Dateigröße + Name)."""
    stat = os.stat(datei_pfad)
    return f"{stat.st_size}_{Path(datei_pfad).name}"


# ─────────────────────────────────────────
# HAUPTPROGRAMM
# ─────────────────────────────────────────

def fotos_sortieren():
    print("=" * 50)
    print("  dotry.ai Foto-Sortierer")
    print("=" * 50)
    print(f"\n📂 Quelle: {QUELL_ORDNER}")
    print(f"📁 Ziel:   {ZIEL_ORDNER}\n")

    # Prüfen ob Quellordner existiert
    if not os.path.exists(QUELL_ORDNER):
        print(f"❌ Quellordner nicht gefunden: {QUELL_ORDNER}")
        print("   Bitte QUELL_ORDNER in den Einstellungen anpassen.")
        return

    # Alle Fotos sammeln
    alle_fotos = [
        f for f in Path(QUELL_ORDNER).rglob("*")
        if f.suffix.lower() in FOTO_TYPEN
    ]

    if not alle_fotos:
        print(f"❌ Keine Fotos gefunden in: {QUELL_ORDNER}")
        return

    print(f"📸 {len(alle_fotos)} Fotos gefunden\n")

    # Zielordner erstellen
    Path(ZIEL_ORDNER).mkdir(parents=True, exist_ok=True)

    # Statistik
    verarbeitet = 0
    uebersprungen = 0
    fehler = 0
    ort_cache = {}  # GPS-Anfragen cachen

    for i, foto_pfad in enumerate(alle_fotos, 1):
        try:
            print(f"[{i}/{len(alle_fotos)}] {foto_pfad.name}", end=" ... ")

            # EXIF lesen
            exif = get_exif_data(foto_pfad)

            # Datum bestimmen
            datum = get_aufnahmedatum(exif, foto_pfad)

            # Ort bestimmen
            koordinaten = get_gps_koordinaten(exif)
            if koordinaten and ORT_ABRUFEN:
                # Cache nutzen um API-Anfragen zu reduzieren
                cache_key = f"{round(koordinaten[0],2)},{round(koordinaten[1],2)}"
                if cache_key not in ort_cache:
                    ort_cache[cache_key] = koordinaten_zu_ort(*koordinaten)
                ort = ort_cache[cache_key]
            else:
                ort = "Unbekannt"

            # Zielordner bestimmen
            ziel_unterordner = ordner_name(datum, ort)
            ziel_pfad = Path(ZIEL_ORDNER) / ziel_unterordner
            ziel_pfad.mkdir(parents=True, exist_ok=True)

            # Zieldatei
            ziel_datei = ziel_pfad / foto_pfad.name

            # Duplikat-Prüfung
            if DUPLIKATE_UEBERSPRINGEN and ziel_datei.exists():
                print(f"⏭️  Duplikat")
                uebersprungen += 1
                continue

            # Kopieren (nicht verschieben – sicherer!)
            shutil.copy2(foto_pfad, ziel_datei)
            print(f"✅ → {ziel_unterordner}/")
            verarbeitet += 1

        except Exception as e:
            print(f"❌ Fehler: {e}")
            fehler += 1

    # Zusammenfassung
    print("\n" + "=" * 50)
    print(f"  Fertig! 🎉")
    print(f"  ✅ Sortiert:     {verarbeitet}")
    print(f"  ⏭️  Übersprungen: {uebersprungen}")
    print(f"  ❌ Fehler:       {fehler}")
    print(f"  📁 Zielordner:   {ZIEL_ORDNER}")
    print("=" * 50)


if __name__ == "__main__":
    fotos_sortieren()
