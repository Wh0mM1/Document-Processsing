import hashlib
import json
import re
import subprocess
from pathlib import Path


class IngestionError(ValueError):
    pass


def read_pdf(path):
    source = Path(path).expanduser().resolve()
    if not source.is_file() or source.suffix.lower() != '.pdf':
        raise IngestionError('A readable PDF source is required.')
    from pypdf import PdfReader
    reader = PdfReader(str(source))
    if reader.is_encrypted and reader.decrypt('') == 0:
        raise IngestionError(
            'Password-protected PDFs require a separate decryption step.')
    pages = [{'page': n, 'text': (p.extract_text() or '').replace(
        '\x00', ' ').strip()} for n, p in enumerate(reader.pages, 1)]
    if not any(p['text'] for p in pages):
        raise IngestionError('No extractable text; OCR required.')
    return hashlib.sha256(source.read_bytes()).hexdigest(), pages, [f"Page {p['page']} needs OCR before it can be trusted." for p in pages if len(p['text']) < 24]


def analyse_pdf(path, archive_root='data/documents'):
    """Preserve a source PDF as pages, layout, table candidates, visuals and prose."""
    import fitz
    import pdfplumber
    source = Path(path).expanduser().resolve()
    document_id = hashlib.sha256(source.read_bytes()).hexdigest()
    root = Path(archive_root)/document_id
    root.mkdir(parents=True, exist_ok=True)
    original = root/'original.pdf'
    if not original.exists():
        original.write_bytes(source.read_bytes())
    pdf = fitz.open(str(source))
    warnings = []
    pages = []
    sections = []
    with pdfplumber.open(str(source)) as plumber:
        for number, page in enumerate(pdf, 1):
            text = page.get_text('text').replace('\x00', ' ').strip()
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            page_image = root/f'page-{number:03}.png'
            pix.save(str(page_image))
            blocks = [{'bbox': [round(v, 1) for v in block[:4]], 'text': block[4].strip(
            ), 'type': int(block[6])} for block in page.get_text('blocks') if block[4].strip()]
            visuals = []
            image_area = 0
            for image_number, img in enumerate(page.get_images(full=True), 1):
                xref = img[0]
                info = pdf.extract_image(xref)
                ext = info.get('ext', 'bin')
                asset = root/f'p{number:03}-image-{image_number:02}.{ext}'
                asset.write_bytes(info['image'])
                rects = page.get_image_rects(xref)
                bbox = [round(v, 1) for v in rects[0]] if rects else None
                if bbox:
                    image_area += max(0, (bbox[2]-bbox[0])*(bbox[3]-bbox[1]))
                visuals.append({'asset_path': str(
                    asset), 'xref': xref, 'kind': 'chart_or_image', 'bbox': bbox, 'source_page': number})
            candidates = []
            for candidate in plumber.pages[number-1].find_tables():
                rows = candidate.extract() or []
                if len(rows) >= 2 and max((len(row) for row in rows), default=0) >= 2:
                    candidates.append({'bbox': [round(v, 1) for v in candidate.bbox], 'rows': rows, 'source_page': number, 'cell_citations': [
                                      [{'page': number, 'bbox': [round(v, 1) for v in candidate.bbox]} for _ in row] for row in rows]})
            page_area = page.rect.width*page.rect.height
            image_heavy = bool(visuals) and (
                len(text) < 350 or image_area/page_area > 0.35)
            ocr_text = ''
            ocr_words = []
            if image_heavy:
                try:
                    result = subprocess.run(['tesseract', str(
                        page_image), 'stdout', '--psm', '6', 'tsv'], capture_output=True, text=True, timeout=90, check=False)
                    rows = result.stdout.splitlines()[1:]
                    for row in rows:
                        fields = row.split('\t')
                        if len(fields) == 12 and fields[11].strip():
                            ocr_words.append({'text': fields[11].strip(), 'bbox': [int(fields[6]), int(fields[7]), int(
                                fields[6])+int(fields[8]), int(fields[7])+int(fields[9])], 'confidence': float(fields[10])})
                    ocr_text = ' '.join(word['text'] for word in ocr_words)
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    warnings.append(
                        f'Page {number} needs OCR but tesseract was unavailable.')
            # Page-level prose is retained separately; it alone becomes retrieval chunks.
            narrative = []
            for line in text.splitlines():
                clean = re.sub(r'\s+', ' ', line).strip()
                if len(clean) >= 40 and ('•' in clean or clean.endswith('.') or clean.startswith('Outlook')):
                    narrative.append({'text': clean, 'source_page': number})
            title = next((b['text'] for b in blocks if len(b['text']) < 100 and (
                b['text'].istitle() or b['text'].isupper())), f'Page {number}')
            sections.append({'title': title, 'start_page': number, 'end_page': number, 'kind': 'boilerplate' if number == len(
                pdf) and 'DISCLAIMER' in text.upper() else 'research'})
            effective_text = text+'\n'+ocr_text
            if len(effective_text) < 24:
                warnings.append(
                    f'Page {number} needs OCR before it can be trusted.')
            pages.append({'page': number, 'text': text, 'ocr_text': ocr_text, 'ocr_words': ocr_words, 'page_type': 'image_heavy' if image_heavy else 'text_native', 'page_image_path': str(
                page_image), 'ocr_status': 'completed' if ocr_text else ('not_required' if not image_heavy else 'required'), 'layout_blocks': blocks, 'tables': candidates, 'visuals': visuals, 'narrative_blocks': narrative})
    manifest = {'document_id': document_id, 'original_pdf_path': str(
        original), 'pages': pages, 'sections': sections, 'warnings': warnings}
    (root/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest
