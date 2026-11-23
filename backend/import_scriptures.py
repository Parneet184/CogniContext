"""Run: python -m backend.import_scriptures --file corpus.csv --edition-id ..."""
import argparse
from .local_db import import_records, read_dataset, stats

def main():
    p = argparse.ArgumentParser(description='Import a legally sourced scripture dataset into local SQLite')
    p.add_argument('--file',required=True)
    p.add_argument('--edition-id',required=True)
    p.add_argument('--title',required=True)
    p.add_argument('--source-url',required=True)
    p.add_argument('--rights-note',required=True)
    p.add_argument('--publisher',default='')
    p.add_argument('--update',action='store_true')
    a = p.parse_args()
    n = import_records(read_dataset(a.file),edition_id=a.edition_id,title=a.title,source_url=a.source_url,rights_note=a.rights_note,publisher=a.publisher,allow_update=a.update)
    print(f'Imported {n} unreviewed records. Counts: {stats()}')
if __name__ == '__main__': main()
