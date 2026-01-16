import pydicom
import numpy as np
from PIL import Image
from pathlib import Path
from pydicom.multival import MultiValue

def _get_dicom_value(dataset, keyword, default=None):
    """Pomocná funkce pro bezpečné získání hodnoty z DICOM datasetu."""
    val = getattr(dataset, keyword, default)
    # Někdy pydicom vrátí objekt, který má atribut .value, jindy přímo hodnotu
    if hasattr(val, 'value'):
        return val.value
    return val

def get_drl_metadata(path):
    """
    Načte metadata z DICOM souboru potřebná pro DRL analýzu.
    """
    try:
        ds = pydicom.dcmread(path)
        
        # 1. Základní údaje o pacientovi
        patient_id = _get_dicom_value(ds, 'PatientID', 'N/A')
        
        sex_raw = _get_dicom_value(ds, 'PatientSex', 'N/A')
        sex_map = {'M': 'Muž', 'F': 'Žena'}
        sex = sex_map.get(sex_raw, sex_raw)
        
        weight = _get_dicom_value(ds, 'PatientWeight', 'N/A')

        # 2. Popis a datum (použití pydicom keywords místo hex tagů)
        study_desc = _get_dicom_value(ds, 'StudyDescription', 'Neznámé vyšetření')
        date_raw = _get_dicom_value(ds, 'StudyDate', "")
        
        # Formátování data YYYYMMDD -> DD.MM.YYYY
        date_str = str(date_raw)
        if len(date_str) == 8:
            study_date = f"{date_str[6:8]}.{date_str[4:6]}.{date_str[0:4]}"
        else:
            study_date = "---"

        # 3. Výpočet KAP (Image Area Dose Product)
        # Tag (0018, 115E) correspond to ImageAreaDoseProduct
        kap_raw = ds.get((0x0018, 0x115e), None)
        
        if kap_raw is not None:
            # Původní logika: násobení 100.0 pro převod jednotek
            kap = round(float(kap_raw.value) * 100.0, 2)
        else:
            kap = "N/A"

        return {
            "path": str(path),
            "filename": path.name,
            "PatientID": patient_id,
            "Sex": sex,
            "Weight": weight,
            "KAP": kap,
            "StudyDescription": study_desc,
            "StudyDate": study_date
        }
    except Exception as e:
        return {"error": str(e), "filename": path.name}

def generate_thumb(dicom_path, thumb_folder):
    """
    Vytvoří kontrastní PNG náhled aplikací Window Center/Width nebo auto-levelingu.
    """
    try:
        ds = pydicom.dcmread(dicom_path)
        img_array = ds.pixel_array.astype(float)

        # Načtení Window Center (WC) a Window Width (WW)
        wc_attr = ds.get('WindowCenter')
        ww_attr = ds.get('WindowWidth')

        if wc_attr and ww_attr:
            # Ošetření, pokud je hodnota seznam (MultiValue) - bereme první
            wc = wc_attr[0] if isinstance(wc_attr, MultiValue) else wc_attr
            ww = ww_attr[0] if isinstance(ww_attr, MultiValue) else ww_attr
            
            low = wc - (ww / 2)
            high = wc + (ww / 2)
        else:
            # Fallback: Automatický kontrast (1. a 99. percentil)
            low, high = np.percentile(img_array, (1, 99))

        # Aplikace ořezu a normalizace na 0-255
        img_array = np.clip(img_array, low, high)
        if high != low: # Prevence dělení nulou
            img_array = (img_array - low) / (high - low) * 255.0

        # Invertování barev pro MONOCHROME1 (rentgen: kosti mají být bílé)
        photometric = _get_dicom_value(ds, 'PhotometricInterpretation', '')
        if photometric == "MONOCHROME1":
            img_array = 255.0 - img_array

        # Uložení obrázku
        img = Image.fromarray(np.uint8(img_array))
        img.thumbnail((300, 300))
        
        thumb_filename = f"{dicom_path.stem}.png"
        thumb_path = Path(thumb_folder) / thumb_filename
        img.save(thumb_path)
        
        return thumb_filename

    except Exception as e:
        print(f"Nelze vytvořit náhled pro {dicom_path.name}: {e}")
        return "default_thumb.png"