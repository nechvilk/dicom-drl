import os
import sys
import shutil
import pandas as pd
import io
import csv
from pathlib import Path
from flask import Flask, render_template, request, make_response

# --- AUTO-FIX PRO IMPORTY (aby fungovalo spouštění odkudkoliv) ---
current_file = Path(__file__).resolve()
src_path = str(current_file.parent.parent.parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from dicom_drl.core.logic import get_drl_metadata, generate_thumb

# --- KONFIGURACE ---
WEB_DIR = current_file.parent
template_dir = str(WEB_DIR / "templates")
static_dir = str(WEB_DIR / "static")
THUMB_DATA = WEB_DIR / "static" / "thumbnails"

# Cesta k datům: Buď nastavená přes Docker (ENV), nebo výchozí '/app/data'
DATA_DIR = Path(os.getenv('DICOM_DATA_DIR', '/app/data'))

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

def create_app():
    """Tovární funkce pro vytvoření aplikace (pro main.py nebo Gunicorn)."""
    # Při startu zajistíme, že existují potřebné složky
    THUMB_DATA.mkdir(parents=True, exist_ok=True)
    if not DATA_DIR.exists():
        print(f"VAROVÁNÍ: Vstupní složka {DATA_DIR} neexistuje! Vytvářím prázdnou.")
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    return app

# --- ROUTES ---
@app.route('/')
def index():
    """Automaticky skenuje DATA_DIR."""
    
    # --- ZAČÁTEK OPRAVY (Fix pro Docker Volume) ---
    # Nemůžeme smazat THUMB_DATA (shutil.rmtree), protože je to mount point.
    # Místo toho projdeme obsah a smažeme soubory uvnitř.
    if THUMB_DATA.exists():
        for item in THUMB_DATA.iterdir():
            try:
                if item.is_file() or item.is_symlink():
                    item.unlink()  # Smaže soubor
                elif item.is_dir():
                    shutil.rmtree(item)  # Smaže podsložku
            except Exception as e:
                print(f"Nepodařilo se smazat {item.name}: {e}")
    else:
        THUMB_DATA.mkdir(parents=True, exist_ok=True)
    # --- KONEC OPRAVY ---

    files_info = []
    
    # Skenujeme složku definovanou v Dockeru (Zbytek kódu je Váš původní)
    if DATA_DIR.exists():
        for f in DATA_DIR.glob('*'):
            # Ignorujeme skryté soubory a systémové složky
            if f.is_file() and not f.name.startswith('.'):
                try:
                    meta = get_drl_metadata(f)
                    if "error" not in meta:
                        thumb_name = generate_thumb(f, THUMB_DATA)
                        meta['thumb_url'] = thumb_name
                        files_info.append(meta)
                except Exception as e:
                    print(f"Skipping {f.name}: {e}")
    
    return render_template('selection.html', 
                           files=files_info, 
                           current_path=str(DATA_DIR))

@app.route('/process', methods=['POST'])
def process():
    selected_paths = request.form.getlist('selected_files')
    
    if not selected_paths:
        return "Nebyly vybrány žádné soubory. <a href='/'>Zpět</a>", 400

    results = []
    for path_str in selected_paths:
        file_path = Path(path_str)
        if file_path.exists():
            meta = get_drl_metadata(file_path)
            if "error" not in meta and meta["KAP"] != "N/A":
                results.append({
                    "ID": meta["PatientID"],
                    "Weight": float(meta["Weight"]) if meta["Weight"] and meta["Weight"] != "N/A" else None,
                    "KAP": float(meta["KAP"]),
                    "Date": meta.get("StudyDate", "---"),
                    "Description": meta.get("StudyDescription", "---"),
                    "Filename": meta["filename"],
                    "Path": str(file_path)
                })

    if not results:
        return "Data neobsahují platné KAP hodnoty. <a href='/'>Zpět</a>", 400

    df = pd.DataFrame(results)
    
    summary = {
        "count": len(df),
        "mean": round(df["KAP"].mean(), 2),
        "median": round(df["KAP"].median(), 2),
        "weight_mean": round(df["Weight"].mean(), 1) if not df["Weight"].isnull().all() else "N/A",
    }
    
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
        return "Chyba exportu", 400

    df_main = pd.DataFrame(individual_data)
    count = len(df_main)
    mean_kap = round(pd.to_numeric(df_main["KAP_mGycm2"], errors='coerce').mean(), 2)
    median_kap = round(pd.to_numeric(df_main["KAP_mGycm2"], errors='coerce').median(), 2)
    mean_weight = round(pd.to_numeric(df_main["Hmotnost_kg"], errors='coerce').mean(), 1)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    
    writer.writerow(["SOUHRNNA_STATISTIKA"])
    writer.writerow(["Pocet_snimku", count])
    writer.writerow(["Prumerny_KAP", mean_kap])
    writer.writerow(["Median_KAP", median_kap])
    writer.writerow(["Prumerna_hmotnost", mean_weight])
    writer.writerow([])
    writer.writerow(["Pacient_ID", "Datum", "Hmotnost_kg", "KAP_mGycm2", "Popis_vysetreni", "Nazev_souboru"])
    
    for index, row in df_main.iterrows():
        writer.writerow(row.values)
    
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=drl_export.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8-sig"
    return response

# Toto zůstává jen pro lokální ladění mimo Docker
if __name__ == "__main__":
    create_app()
    app.run(debug=True, port=5000)