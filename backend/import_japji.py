"""Import the extracted Japji Sahib JSON into the project's local SQLite database.
Run from the project root: python -m backend.import_japji
"""
from pathlib import Path
from .japji_db import import_pauris, list_pauris

DEFAULT_JSON = Path(__file__).resolve().parents[1] / 'backend' / 'data_templates' / 'japji_pauris_extracted.json'

def main():
    count = import_pauris(DEFAULT_JSON)
    rows = list_pauris()
    print(f'Imported/updated {count} Pauris into SQLite.')
    print(f'Verification: {len(rows)} records; Pauri numbers {rows[0]["pauri_number"]}–{rows[-1]["pauri_number"]}.')
    print('Emotion mappings are intentionally empty until the user reviews them.')

if __name__ == '__main__':
    main()
