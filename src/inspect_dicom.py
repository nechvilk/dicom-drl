import pydicom
from pathlib import Path

# 1. Nastavení cest
base_dir = Path(__file__).resolve().parent.parent
data_path = base_dir / "data" / "raw"
files = sorted(list(data_path.glob("*"))) # Seřazeno pro konzistenci

if not files:
    print(f"Složka {data_path} je prázdná.")
    exit()

# Načtení prvního souboru
dcm_file = files[19]
ds = pydicom.dcmread(dcm_file)

print(f"=== ANALÝZA: {dcm_file.name} ===")
print(f"Přístroj: {ds.get('Manufacturer', 'N/A')} {ds.get('ManufacturerModelName', 'N/A')}")
print("-" * 40)

# 2. Funkce pro bezpečné prohledávání všeho (i vnořených sekvencí)
def find_dose_info(dataset, indent=0):
    for element in dataset:
        # Pokud je to sekvence, vlezeme dovnitř
        if element.VR == "SQ":
            for i, item in enumerate(element.value):
                find_dose_info(item, indent + 2)
        else:
            # Hledáme klíčová slova v názvu tagu
            name = element.name
            if any(word in name for word in ["Dose", "Exposure", "Output", "KVP"]):
                # Ošetření None hodnot a formátování
                val = element.value
                space = " " * indent
                print(f"{space}{element.tag} | {name: <35} : {val}")

print("Nalezené parametry záření a dávky:")
find_dose_info(ds)

# 3. Specifický výpis důležitých hodnot pro DRL (pokud existují)
print("\n--- Souhrn pro výpočet ---")
important_tags = [
    (0x0018, 0x0060), # KVP
    (0x0018, 0x115E), # ImageAndFluoroscopyAreaDoseProduct
    (0x0018, 0x9332), # ExposureInmAs
    (0x0018, 0x1110), # DistanceSourceToDetector
]

for tag in important_tags:
    if tag in ds:
        el = ds[tag]
        print(f"{el.name: <35}: {el.value}")

print("\n=== Hotovo ===")