import pydicom
from pathlib import Path

dcm_file = list(Path("data/raw").glob("*"))[3]
ds = pydicom.dcmread(dcm_file)

print(ds.get("DeviceSerialNumber", "N/A"))
print(ds.get("ManufacturerModelName", "N/A"))
print(ds.get("ImageComments", "N/A"))

for element in ds:
    if element.VR in ["DS", "IS", "FL", "FD"]: # Všechny číselné typy
        print(f"{element.tag} {element.name}: {element.value}")

print(f"--- Detailní rozbor dávky: {dcm_file.name} ---")

# 1. Klasické hledání v ploše
for element in ds:
    if any(word in element.name for word in ["Dose", "Area", "Unit"]):
        print(f"Tag: {element.tag} | {element.name}: {element.value}")

# 2. Hledání v sekvencích (tady bývají jednotky schované)
if "ExposureDoseSequence" in ds:
    print("\n--- Obsah ExposureDoseSequence ---")
    for item in ds.ExposureDoseSequence:
        for sub_el in item:
            print(f"  Sub-Tag: {sub_el.tag} | {sub_el.name}: {sub_el.value}")
