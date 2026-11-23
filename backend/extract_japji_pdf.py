"""Extract Japji Sahib Pauris from the supplied PDF into structured JSON.

Usage from project root:
  python -m backend.extract_japji_pdf
  python -m backend.extract_japji_pdf --pdf path/to/file.pdf --output backend/data_templates/japji_pauris_extracted.json
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
import fitz

DEFAULT_PDF = Path(__file__).resolve().parent / 'data_templates' / 'Japji-Sahib-GRE.pdf'
DEFAULT_OUTPUT = Path(__file__).resolve().parent / 'data_templates' / 'japji_pauris_extracted.json'

def clean_lines(block_text: str) -> list[str]:
    ascii_text = block_text.encode('ascii', errors='ignore').decode('ascii')
    out=[]
    for line in ascii_text.splitlines():
        line=re.sub(r'\|\|\s*\d+\s*\|\|',' ',line)
        line=re.sub(r'\s+',' ',line).strip()
        line=re.sub(r'[^A-Za-z0-9.,;:!?()\-\'" ]',' ',line)
        line=re.sub(r'\s+',' ',line).strip()
        if len(re.findall(r'[A-Za-z]',line)) >= 2:
            out.append(line)
    return out

def extract(pdf_path: Path) -> dict:
    doc=fitz.open(pdf_path)
    records=[]; current=None
    salok={'transliteration':[],'english_translation':[],'pdf_page_start':None,'pdf_page_end':None}
    started=False; in_salok=False
    for page_no,page in enumerate(doc,1):
        for block in page.get_text('blocks'):
            lines=clean_lines(block[4])
            if not lines: continue
            raw_ascii=block[4].encode('ascii',errors='ignore').decode('ascii')
            nums=[int(x) for x in re.findall(r'\|\|\s*(\d+)\s*\|\|',raw_ascii)]
            if not started:
                if nums and nums[0] == 1: started=True
                continue
            if any(line.lower().startswith(('salok','shalok')) for line in lines):
                in_salok=True; continue
            translit=lines[0]; translation=' '.join(lines[1:]).strip()
            if in_salok:
                if salok['pdf_page_start'] is None: salok['pdf_page_start']=page_no
                salok['pdf_page_end']=page_no
                salok['transliteration'].append(translit)
                if translation: salok['english_translation'].append(translation)
                continue
            if current is None:
                current={'pauri_number':len(records)+1,'source_title':'Japji Sahib','source_file':pdf_path.name,
                         'pdf_page_start':page_no,'pdf_page_end':page_no,'transliteration':[],'english_translation':[],
                         'extraction_status':'needs_review','original_gurmukhi':None,'emotions':[]}
            current['pdf_page_end']=page_no
            current['transliteration'].append(translit)
            if translation: current['english_translation'].append(translation)
            if nums and nums[-1] == current['pauri_number']:
                current['transliteration']='\n'.join(current['transliteration'])
                current['english_translation']='\n'.join(current['english_translation'])
                current['combined_text']=current['transliteration']+'\n'+current['english_translation']
                records.append(current); current=None
    if len(records)!=38 or [r['pauri_number'] for r in records] != list(range(1,39)) or current is not None:
        raise ValueError(f'Expected exactly 38 sequential Pauris; extracted {[r["pauri_number"] for r in records]}')
    salok_obj={'transliteration':'\n'.join(salok['transliteration']),
               'english_translation':'\n'.join(salok['english_translation']),
               'pdf_page_start':salok['pdf_page_start'],'pdf_page_end':salok['pdf_page_end'],
               'extraction_status':'needs_review','emotions':[]}
    return {'source':{'title':'Japji Sahib','file':pdf_path.name,'pages':len(doc),
                      'extraction_note':'Romanized Punjabi and English are extracted from PDF text blocks. The embedded Gurmukhi glyph mapping is not extractable as valid Unicode from this PDF; original_gurmukhi is null and must be sourced/verified separately.'},
            'pauris':records,'concluding_salok':salok_obj}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--pdf',type=Path,default=DEFAULT_PDF)
    parser.add_argument('--output',type=Path,default=DEFAULT_OUTPUT)
    args=parser.parse_args()
    payload=extract(args.pdf)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Extracted {len(payload["pauris"])} Pauris and concluding Salok to {args.output}')
    print('Review the transliteration and English translation before public use.')

if __name__=='__main__': main()
