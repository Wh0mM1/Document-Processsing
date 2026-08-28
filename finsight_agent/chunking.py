import re


def structure_aware_chunks(document_id, pages, max_chars=1000, overlap_lines=1):
    chunks = []
    for page in pages:
        current = []
        for line in [re.sub(r'\s+', ' ', x).strip() for x in page['text'].splitlines() if x.strip()]:
            if current and len('\n'.join(current))+len(line)+1 > max_chars:
                chunks.append({'id': f"{document_id}:p{page['page']}:c{len(chunks)}",
                              'document_id': document_id, 'page': page['page'], 'text': '\n'.join(current)})
                current = current[-overlap_lines:]
            current.append(line)
        if current:
            chunks.append({'id': f"{document_id}:p{page['page']}:c{len(chunks)}",
                          'document_id': document_id, 'page': page['page'], 'text': '\n'.join(current)})
    return chunks
