import os
import sys
from pathlib import Path

# Zajistí, že Python uvidí moduly ve složce src (důležité pro lokální spouštění na Archu)
current_path = Path(__file__).resolve().parent
src_path = current_path / "src"
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from dicom_drl.web.app import create_app

def main():
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 5000))
    
    app = create_app()
    app.run(host=host, port=port)

if __name__ == "__main__":
    main()