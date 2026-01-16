import csv
import io
import os
from pathlib import Path

import pandas as pd
from flask import Flask, render_template, request, make_response
import sys

# Získá cestu ke složce 'src' relativně k umístění app.py
base_path = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(base_path))

# Importy z vlastních modulů
from dicom_drl.core.logic import get_drl_metadata, generate_thumb

# --- NASTAVENÍ CEST ---
CURRENT_FILE = Path(__file__).resolve()
WEB_DIR = CURRENT_FILE.parent
SRC_DIR = WEB_DIR.parent
PROJECT_ROOT = SRC_DIR.parent.parent

# Složky pro Flask
TEMPLATE_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"

# Složky pro data
RAW_DATA = PROJECT_ROOT / "data" / "raw"
THUMB_DATA = WEB_DIR / "static" / "thumbnails"

app = Flask(__name__, 
            template_folder=str(TEMPLATE_DIR), 
            static_folder=str(STATIC_DIR))


# --- TRASY (ROUTES) ---

@app.route('/')
def index():
    """Hlavní stránka s výběrem DICOM souborů a generováním náhledů."""
    THUMB_DATA.mkdir(parents=True, exist_ok=True)
    
    files_info = []
    if RAW_DATA.exists():
        # Iterace přes soubory, ignorování skrytých
        for f in RAW_DATA.glob('*'):
            if f.is_file() and not f.name.startswith('.'):
                try:
                    meta = get_drl_metadata(f)
                    if "error" not in meta:
                        # Generování náhledu - vrací jen název souboru (zachována původní funkčnost)
                        thumb_name = generate_thumb(f, THUMB_DATA)
                        meta['thumb_url'] = thumb_name
                        files_info.append(meta)
                except Exception as e:
                    print(f"Chyba při zpracování {f.name}: {e}")
    
    return render_template('selection.html', files=files_info)


@app.route('/process', methods=['POST'])
def process():
    """Zpracování vybraných snímků a výpočet statistik."""
    selected_paths = request.form.getlist('selected_files')
    
    if not selected_paths:
        return "Nebyly vybrány žádné soubory. <a href='/'>Zpět</a>", 400

    results = []
    for path_str in selected_paths:
        file_path = Path(path_str)
        if file_path.exists():
            meta = get_drl_metadata(file_path)
            
            # Filtrace platných dat
            if "error" not in meta and meta["KAP"] != "N/A":
                try:
                    # Bezpečné získání váhy
                    weight = None
                    if meta["Weight"] and meta["Weight"] != "N/A":
                        weight = float(meta["Weight"])

                    results.append({
                        "ID": meta["PatientID"],
                        "Weight": weight,
                        "KAP": float(meta["KAP"]),
                        "Date": meta.get("StudyDate", "---"),
                        "Description": meta.get("StudyDescription", "---"),
                        "Filename": meta["filename"],
                        "Path": str(file_path)
                    })
                except (ValueError, TypeError):
                    continue

    if not results:
        return "Vybrané soubory neobsahují platná data pro KAP. <a href='/'>Zpět</a>", 400

    df = pd.DataFrame(results)
    
    # Výpočet statistik
    summary = {
        "count": len(df),
        "mean": round(df["KAP"].mean(), 2),
        "median": round(df["KAP"].median(), 2),
        "weight_mean": "N/A",
    }
    
    if not df["Weight"].isnull().all():
        summary["weight_mean"] = round(df["Weight"].mean(), 1)
    
    # Referenční skupina (60-80 kg)
    ref_df = df[(df['Weight'] >= 60) & (df['Weight'] <= 80)]
    ref_summary = None
    if not ref_df.empty:
        ref_summary = {
            "count": len(ref_df),
            "mean": round(ref_df["KAP"].mean(), 2)
        }

    return render_template('results.html', 
                           summary=summary, 
                           ref_summary=ref_summary,
                           individual_data=results)


@app.route('/export', methods=['POST'])
def export():
    """Export statistik a dat do CSV (kompatibilní s Excel)."""
    selected_files = request.form.getlist('selected_files')
    
    individual_data = []
    for f_path in selected_files:
        meta = get_drl_metadata(Path(f_path))
        if "error" not in meta:
            individual_data.append({
                "Pacient_ID": meta["PatientID"],
                "Datum": meta["StudyDate"],
                "Hmotnost_kg": meta["Weight"],
                "KAP_mGycm2": meta["KAP"],
                "Popis_vysetreni": meta["StudyDescription"],
                "Nazev_souboru": meta["filename"]
            })
    
    if not individual_data:
        return "Žádná data k exportu", 400

    df_main = pd.DataFrame(individual_data)
    
    # Statistiky pro export
    count = len(df_main)
    mean_kap = round(pd.to_numeric(df_main["KAP_mGycm2"], errors='coerce').mean(), 2)
    median_kap = round(pd.to_numeric(df_main["KAP_mGycm2"], errors='coerce').median(), 2)
    mean_weight = round(pd.to_numeric(df_main["Hmotnost_kg"], errors='coerce').mean(), 1)

    output = io.StringIO()
    # Nastavení CSV pro český Excel (středník jako oddělovač)
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    
    # 1. Zápis souhrnu
    writer.writerow(["SOUHRNNA_STATISTIKA"])
    writer.writerow(["Pocet_snimku", count])
    writer.writerow(["Prumerny_KAP", mean_kap])
    writer.writerow(["Median_KAP", median_kap])
    writer.writerow(["Prumerna_hmotnost", mean_weight])
    writer.writerow([])
    
    # 2. Zápis dat
    writer.writerow(["Pacient_ID", "Datum", "Hmotnost_kg", "KAP_mGycm2", "Popis_vysetreni", "Nazev_souboru"])
    for _, row in df_main.iterrows():
        writer.writerow(row.values)
    
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=drl_export_kompletni.csv"
    # BOM pro správnou diakritiku v Excelu
    response.headers["Content-type"] = "text/csv; charset=utf-8-sig"
    
    return response

if __name__ == "__main__":
    print("--- START SERVERU ---")
    print(f"Hledám DICOM soubory v: {RAW_DATA}")
    print(f"Ukládám náhledy do: {THUMB_DATA}")
    app.run(debug=True, port=5000)