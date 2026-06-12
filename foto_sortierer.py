#!/usr/bin/env python3
"""
dotry.ai – Session 10: Foto-Sortierer für iPhone & Android
===========================================================
Sortiert Smartphone-Fotos automatisch nach Aufnahmedatum und Ort.

Funktioniert für:
  • iPhone / iOS Fotos
  • Android Fotos aus DCIM/Camera

Voraussetzung:
  Die Fotos enthalten EXIF-Daten. GPS funktioniert nur, wenn beim Fotografieren
  der Standortzugriff erlaubt war.

Zielstruktur:
  Fotos_Sortiert/
  ├── 2026-05 – Wien/
  │   ├── IMG_001.jpg
  │   └── IMG_002.jpg
  ├── 2026-06 – Kreta/
  │   └── IMG_003.jpg
  └── 2026-06 – Unbekannt/
      └── IMG_004.jpg

Installation:
  pip install Pillow requests pillow-heif

Start:
  python3 foto_sortierer.py
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
except ImportError:
    print("❌ Pillow nicht installiert.")
    print("   Bitte ausführen: pip install Pillow")
    raise SystemExit(1)

# Optional: HEIC/HEIF-Unterstützung, wenn installiert
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:
    pass

try:
    import requests
except ImportError:
    print("❌ requests nicht installiert.")
    print("   Bitte ausführen: pip install requests")
    raise SystemExit(1)

# ─────────────────────────────────────────
# EINSTELLUNGEN
# ─────────────────────────────────────────

# Du kannst QUELL_ORDNER direkt setzen, z.B.:
# QUELL_ORDNER = os.path.expanduser("~/Desktop/iPhone_Fotos")
# QUELL_ORDNER = os.path.expanduser("~/Desktop/Android_Fotos")
# Wenn None, sucht das Script automatisch typische Ordner.
QUELL_ORDNER = None

ZIEL_ORDNER = os.path.expanduser("~/Desktop/Fotos_Sortiert")

FOTO_TYPEN = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".tiff", ".tif"}
ORT_ABRUFEN = True
DUPLIKATE_UEBERSPRINGEN = True

# Typische lokale Ordner, nachdem du Fotos vom Smartphone kopiert/exportiert hast.
AUTO_QUELL_ORDNER = [
    "~/Desktop/iPhone_Fotos",
    "~/Desktop/Android_Fotos",
    "~/Desktop/Fotos",
    "~/Pictures/iPhone_Fotos",
    "~/Pictures/Android_Fotos",
    "~/Pictures/Fotos",
]

# ─────────────────────────────────────────
# HILFSFUNKTIONEN
# ─────────────────────────────────────────

def finde_quellordner():
    if QUELL_ORDNER:
        return os.path.expanduser(QUELL_ORDNER)
    for kandidat in AUTO_QUELL_ORDNER:
        pfad = os.path.expanduser(kandidat)
        if os.path.exists(pfad):
            return pfad
    return os.path.expanduser("~/Desktop/iPhone_Fotos")


def get_exif_data(bild_pfad):
    try:
        with Image.open(bild_pfad) as img:
            exif_raw = img.getexif()
            if not exif_raw:
                return {}
            return {TAGS.get(tag, tag): wert for tag, wert in exif_raw.items()}
    except Exception:
        return {}


def get_gps_koordinaten(exif_data):
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
            if ref in ["S", "W"]:
                dezimal = -dezimal
            return dezimal

        lat = dms_to_dezimal(gps["GPSLatitude"], gps["GPSLatitudeRef"])
        lon = dms_to_dezimal(gps["GPSLongitude"], gps["GPSLongitudeRef"])
        return lat, lon
    except Exception:
        return None


def koordinaten_zu_ort(lat, lon):
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "zoom": 10,
            "accept-language": "de",
        }
        headers = {"User-Agent": "dotry-ai-foto-sortierer/2.0"}
        resp = requests.get(url, params=params, headers=headers, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        address = data.get("address", {})
        return (
            address.get("city") or
            address.get("town") or
            address.get("village") or
            address.get("municipality") or
            address.get("state") or
            address.get("country") or
            "Unbekannt"
        )
    except Exception:
        return "Unbekannt"


def get_aufnahmedatum(exif_data, datei_pfad):
    datum_str = exif_data.get("DateTimeOriginal") or exif_data.get("DateTime")
    if datum_str:
        try:
            return datetime.strptime(str(datum_str), "%Y:%m:%d %H:%M:%S")
        except Exception:
            pass
    ts = os.path.getmtime(datei_pfad)
    return datetime.fromtimestamp(ts)


def ordner_name(datum, ort):
    monat = datum.strftime("%Y-%m")
    ort_clean = "".join(c for c in ort if c not in r'\\/:*?"<>|').strip() or "Unbekannt"
    return f"{monat} – {ort_clean}"


def eindeutiger_zielpfad(ziel_datei):
    if not ziel_datei.exists():
        return ziel_datei
    stem = ziel_datei.stem
    suffix = ziel_datei.suffix
    parent = ziel_datei.parent
    i = 2
    while True:
        kandidat = parent / f"{stem}_{i}{suffix}"
        if not kandidat.exists():
            return kandidat
        i += 1

# ─────────────────────────────────────────
# HAUPTPROGRAMM
# ─────────────────────────────────────────

def fotos_sortieren():
    quellordner = finde_quellordner()

    print("=" * 56)
    print("  dotry.ai Foto-Sortierer für iPhone & Android")
    print("=" * 56)
    print(f"\n📂 Quelle: {quellordner}")
    print(f"📁 Ziel:   {ZIEL_ORDNER}\n")

    if not os.path.exists(quellordner):
        print(f"❌ Quellordner nicht gefunden: {quellordner}")
        print("   Lege z.B. ~/Desktop/iPhone_Fotos oder ~/Desktop/Android_Fotos an")
        print("   oder setze QUELL_ORDNER oben im Script manuell.")
        return

    alle_fotos = [
        f for f in Path(quellordner).rglob("*")
        if f.is_file() and f.suffix.lower() in FOTO_TYPEN
    ]

    if not alle_fotos:
        print(f"❌ Keine Fotos gefunden in: {quellordner}")
        return

    print(f"📸 {len(alle_fotos)} Fotos gefunden\n")
    Path(ZIEL_ORDNER).mkdir(parents=True, exist_ok=True)

    verarbeitet = 0
    uebersprungen = 0
    fehler = 0
    ort_cache = {}

    for i, foto_pfad in enumerate(alle_fotos, 1):
        try:
            print(f"[{i}/{len(alle_fotos)}] {foto_pfad.name}", end=" ... ")
            exif = get_exif_data(foto_pfad)
            datum = get_aufnahmedatum(exif, foto_pfad)

            koordinaten = get_gps_koordinaten(exif)
            if koordinaten and ORT_ABRUFEN:
                cache_key = f"{round(koordinaten[0], 2)},{round(koordinaten[1], 2)}"
                if cache_key not in ort_cache:
                    ort_cache[cache_key] = koordinaten_zu_ort(*koordinaten)
                ort = ort_cache[cache_key]
            else:
                ort = "Unbekannt"

            ziel_unterordner = ordner_name(datum, ort)
            ziel_pfad = Path(ZIEL_ORDNER) / ziel_unterordner
            ziel_pfad.mkdir(parents=True, exist_ok=True)

            ziel_datei = ziel_pfad / foto_pfad.name
            if DUPLIKATE_UEBERSPRINGEN and ziel_datei.exists():
                print("⏭️  bereits vorhanden")
                uebersprungen += 1
                continue

            ziel_datei = eindeutiger_zielpfad(ziel_datei)
            shutil.copy2(foto_pfad, ziel_datei)
            print(f"✅ → {ziel_unterordner}/")
            verarbeitet += 1

        except Exception as e:
            print(f"❌ Fehler: {e}")
            fehler += 1

    print("\n" + "=" * 56)
    print("  Fertig! 🎉")
    print(f"  ✅ Sortiert:     {verarbeitet}")
    print(f"  ⏭️  Übersprungen: {uebersprungen}")
    print(f"  ❌ Fehler:       {fehler}")
    print(f"  📁 Zielordner:   {ZIEL_ORDNER}")
    print("=" * 56)


if __name__ == "__main__":
    fotos_sortieren()
