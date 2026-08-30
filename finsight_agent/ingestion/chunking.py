import re


def structure_aware_chunks(document_id, pages, max_chars=1000, overlap_lines=1):
    chunks = []
    for page in pages:
        page_num = page.get('page', 1)
        title = page.get('title', f'Page {page_num}')
        header_prefix = f'[Slide {page_num}: {title}]' + chr(10)

        # 1. Structured Tables
        for t_idx, table in enumerate(page.get('tables', [])):
            md_table = table.get('markdown')
            if not md_table and table.get('rows'):
                from .pdf_parser import table_to_markdown
                md_table = table_to_markdown(table['rows'])
            if md_table:
                chunks.append({
                    'id': f'{document_id}:p{page_num}:t{t_idx}',
                    'document_id': document_id,
                    'page': page_num,
                    'type': 'table',
                    'text': header_prefix + 'Table:' + chr(10) + md_table
                })

        # 2. Visual / Chart Summaries (if extracted)
        for v_idx, visual in enumerate(page.get('visuals', [])):
            summary = visual.get('extracted_summary') or visual.get('summary')
            if summary:
                kind = visual.get('kind', 'graphic')
                chunks.append({
                    'id': f'{document_id}:p{page_num}:v{v_idx}',
                    'document_id': document_id,
                    'page': page_num,
                    'type': 'chart',
                    'text': header_prefix + f'Chart/Visual ({kind}):' + chr(10) + summary
                })

        # 3. Narrative & Prose text
        narrative_lines = []
        if page.get('narrative_blocks'):
            narrative_lines = [b['text'] for b in page['narrative_blocks'] if b.get('text')]
        elif page.get('text'):
            narrative_lines = [re.sub(r'\s+', ' ', x).strip() for x in page['text'].splitlines() if x.strip()]

        if narrative_lines:
            current = []
            for line in narrative_lines:
                if current and len(chr(10).join(current)) + len(line) + 1 > max_chars:
                    chunk_text = chr(10).join(current)
                    if not chunk_text.startswith('[Slide'):
                        chunk_text = header_prefix + chunk_text
                    chunks.append({
                        'id': f'{document_id}:p{page_num}:c{len(chunks)}',
                        'document_id': document_id,
                        'page': page_num,
                        'type': 'narrative',
                        'text': chunk_text
                    })
                    current = current[-overlap_lines:]
                current.append(line)
            if current:
                chunk_text = chr(10).join(current)
                if not chunk_text.startswith('[Slide'):
                    chunk_text = header_prefix + chunk_text
                chunks.append({
                    'id': f'{document_id}:p{page_num}:c{len(chunks)}',
                    'document_id': document_id,
                    'page': page_num,
                    'type': 'narrative',
                    'text': chunk_text
                })

    return chunks
