# DICOM DRL Analyzer (DRÚ)

Nástroj pro automatizovanou analýzu a sledování **Diagnostických referenčních úrovní (DRÚ)** z DICOM souborů. Projekt je optimalizován pro běh na **Raspberry Pi** s **Ubuntu Serverem** (headless režim), což umožňuje stabilní a nízkonákladové síťové nasazení.

## 🌟 Hlavní funkce
- **Extrakce parametrů:** Automatické čtení klíčových parametrů (ID pacienta, datum vyšetření, hmotnost pacienta, DAP - dose area pruduct) z DICOM hlaviček.
- **Optimalizace pro RPi:** Navrženo pro provoz jako headless server; veškerá interakce probíhá přes webové rozhraní a sdílenou síťovou složku.
- **Vizuální kontrola:** Automatické generování náhledů (thumbnails) pro rychlé ověření dat v prohlížeči.
- **Export výsledků:** Možnost exportu kompletní analýzy do formátu **CSV** pro další statistické zpracování.
- **Široká podpora DICOM:** Podpora různých kompresních formátů díky integraci `pylibjpeg` a `python-gdcm`.

## 🛠 Technický stack
- **Hardware:** Raspberry Pi 4/5 (Headless).
- **OS:** Ubuntu Server (ARM64).
- **Jazyk:** Python 3.13+ (spravováno přes `uv`).
- **Web:** Flask, Jinja2 šablony.
- **Infrastruktura:** Docker & Docker Compose.

## 📂 Zpracování dat a vstup (Samba / Síťový disk)

Aplikace je navržena pro nasazení, kdy jsou zdrojová data uložena mimo adresář projektu (např. na síťovém úložišti Samba nebo NAS).

1. **Mapování svazků:** V `docker-compose.yaml` je systémová složka (např. `/home/piadmin/dicom_data`) mapována přímo do kontejneru do adresáře `/app/data`.
2. **Persistence náhledů:** Aplikace využívá pojmenovaný Docker volume `thumb_cache`. Díky tomu se náhledy nemusí při restartu kontejneru generovat znovu, což šetří CPU výkon Raspberry Pi.
3. **Konfigurace:** Cesta ke zdrojovým datům je uvnitř kontejneru řízena proměnnou prostředí `DICOM_DATA_DIR`.

## 🚀 Jak aplikaci spustit

### 1. Spuštění přes Docker Compose
Díky Dockeru nemusíte na Raspberry Pi instalovat žádné Python závislosti.
```bash
docker-compose up --build -d
