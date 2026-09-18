"""Dependency-light HouseNet document artifacts (XLSX, DOCX, PDF)."""
from __future__ import annotations
import datetime, html, pathlib, re, zipfile, zlib
ROOT=pathlib.Path(__file__).resolve().parent
ARTIFACTS=ROOT/'.secure'/'generated'; ARTIFACTS.mkdir(parents=True,exist_ok=True)
def _safe(s): return re.sub(r'[^A-Za-z0-9._-]+','-',str(s)).strip('-')[:80] or 'deputy-report'
def _text(data):
 if isinstance(data,dict): return [(str(k), str(v) if not isinstance(v,(dict,list)) else str(v)) for k,v in data.items()]
 if isinstance(data,list): return [(str(i+1),str(x)) for i,x in enumerate(data)]
 return [('Result',str(data))]
def _write_xlsx(path,title,data):
 rows=[(title,''),('Generated',datetime.datetime.now().isoformat())]+_text(data)
 esc=lambda s:html.escape(str(s))
 sheet=''.join(f'<row r="{i}"><c r="A{i}" t="inlineStr"><is><t>{esc(a)}</t></is></c><c r="B{i}" t="inlineStr"><is><t>{esc(b)}</t></is></c></row>' for i,(a,b) in enumerate(rows,1))
 files={'[Content_Types].xml':'<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>','_rels/.rels':'<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>','xl/workbook.xml':'<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="HouseNet" sheetId="1" r:id="rId1"/></sheets></workbook>','xl/_rels/workbook.xml.rels':'<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>','xl/worksheets/sheet1.xml':f'<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{sheet}</sheetData></worksheet>'}
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
  for n,v in files.items(): z.writestr(n,v)
def _write_docx(path,title,data):
 paras=f'<w:p><w:r><w:t>{html.escape(title)}</w:t></w:r></w:p><w:p><w:r><w:t>HouseNet / Deputy</w:t></w:r></w:p>'+''.join(f'<w:p><w:r><w:t>{html.escape(a)}: {html.escape(b)}</w:t></w:r></w:p>' for a,b in _text(data))
 files={'[Content_Types].xml':'<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>','_rels/.rels':'<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>','word/document.xml':f'<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{paras}<w:sectPr/></w:body></w:document>'}
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
  for n,v in files.items(): z.writestr(n,v)
def _write_pdf(path,title,data):
 lines=[title,'HouseNet / Deputy',datetime.datetime.now().isoformat()]+[f'{a}: {b}' for a,b in _text(data)]
 stream='BT /F1 11 Tf 50 760 Td '+' '.join(f'({str(x).replace("(","[").replace(")","]")[:180]}) Tj 0 -16 Td' for x in lines)+' ET'
 objs=['<< /Type /Catalog /Pages 2 0 R >>','<< /Type /Pages /Kids [3 0 R] /Count 1 >>','<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>','<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',f'<< /Length {len(stream.encode())} >>\nstream\n{stream}\nendstream']
 out=b'%PDF-1.4\n'; offs=[]
 for i,o in enumerate(objs,1): offs.append(len(out)); out+=f'{i} 0 obj\n{o}\nendobj\n'.encode()
 x=len(out); out+=f'xref\n0 {len(objs)+1}\n0000000000 65535 f \n'.encode()+b''.join(f'{n:010d} 00000 n \n'.encode() for n in offs)+f'trailer << /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF'.encode(); path.write_bytes(out)
def create(kind,title,data):
 ext={'xlsx':'xlsx','docx':'docx','pdf':'pdf'}[kind]; aid=datetime.datetime.now().strftime('%Y%m%d%H%M%S%f'); p=ARTIFACTS/f'{_safe(title)}-{aid}.{ext}'; {'xlsx':_write_xlsx,'docx':_write_docx,'pdf':_write_pdf}[kind](p,title,data); return {'id':aid,'title':title,'kind':kind,'path':str(p),'created_at':datetime.datetime.now().isoformat(timespec='seconds')}
def list_artifacts():
 return [{'id':p.stem,'title':p.stem.rsplit('-',1)[0],'kind':p.suffix[1:],'created_at':datetime.datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec='seconds'),'size':p.stat().st_size} for p in sorted(ARTIFACTS.iterdir()) if p.is_file()]
