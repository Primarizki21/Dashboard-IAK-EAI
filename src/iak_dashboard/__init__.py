"""
IAK Dashboard Package.
"""
import sys
import uvicorn
from iak_dashboard.etl.pipeline import run_pipeline
from iak_dashboard.etl.schema import DB_PATH

def main():
    if not DB_PATH.exists():
        print(f"[!] Database {DB_PATH} belum ditemukan. Menjalankan ETL terlebih dahulu...")
        run_pipeline()

    print("[*] Menjalankan server IAK Mining Dashboard di http://127.0.0.1:8000 ...")
    uvicorn.run("iak_dashboard.api.app:app", host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":
    main()
