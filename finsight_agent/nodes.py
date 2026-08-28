import re
from .chunking import structure_aware_chunks
from .ingestion import analyse_pdf
from .llm import generate_grounded_summary
from .financial import extract_facts

PLAN = [{'output': 'structured_data', 'topic': 'revenue', 'query': 'revenue revenue from operations growth yoy qoq'}, {'output': 'structured_data', 'topic': 'profitability', 'query': 'EBITDA PAT net profit margin growth'}, {'output': 'chart_specs', 'topic': 'time_series',
                                                                                                                                                                                                                                'query': 'quarterly revenue EBITDA PAT year over year growth chart'}, {'output': 'narrative_sections', 'topic': 'guidance', 'query': 'guidance outlook target demand forecast capex'}, {'output': 'narrative_sections', 'topic': 'risks', 'query': 'risk headwind challenge decline pressure'}]
METRICS = {'revenue': r'revenue(?: from operations)?', 'ebitda': r'\bEBITDA\b',
           'pat': r'\bPAT\b|net profit|profit after tax'}
AMOUNT = r'(?:(?:₹|Rs\.?|INR|USD|\$)\s*)?\d[\d,]*(?:\.\d+)?\s*(?:crore|cr|mn|million|bn|billion)'


def make_nodes(store, embeddings):
    def ingest(state):
        manifest = analyse_pdf(state['source_path'])
        store.save_analysis(manifest)
        return {'document_id': manifest['document_id'], 'pages': manifest['pages'], 'quality_flags': manifest['warnings']}

    def chunk(state):
        narrative_pages = [{'page': page['page'], 'text': '\n'.join(
            block['text'] for block in page.get('narrative_blocks', []))} for page in state['pages']]
        chunks = structure_aware_chunks(state['document_id'], narrative_pages)
        store.index(state['document_id'], state['source_path'],
                    chunks, embeddings.embed([c['text'] for c in chunks]))
        return {'chunks': chunks}

    def plan(state): return {'research_plan': PLAN,
                             'retry_count': state.get('retry_count', 0)}

    def extract_financials(state): return {
        'financial_facts': extract_facts(state['pages'])}

    def retrieve(state):
        evidence = []
        seen = set()
        for task in state['research_plan']:
            for hit in store.search(state['document_id'], embeddings.embed([task['query']])[0], 4+state.get('retry_count', 0)*3):
                if hit['chunk_id'] not in seen:
                    evidence.append({**hit, 'topic': task['topic']})
                    seen.add(hit['chunk_id'])
        return {'retrieved_evidence': evidence}

    def extract(state):
        claims = []
        for evidence in state.get('retrieved_evidence', []):
            safe_text = evidence['text'].replace('Rs. ', 'Rs~')
            for sentence in re.split(r'(?<=[.!?])\s+|(?=\s*[•●])|(?<=[,;])\s+(?=(?:Reported |Consolidated )?(?:Revenue|EBITDA|PAT|Net profit|Net order value))', safe_text):
                sentence = sentence.replace('Rs~', 'Rs. ')
                matches = [(m.start(), name) for name, pattern in METRICS.items() if (
                    m := re.search(pattern, sentence, re.I))]
                if not matches:
                    continue
                value = re.search(
                    rf'\b(?:to|at|was|were|of)\s+({AMOUNT})\b', sentence, re.I) or re.search(rf'({AMOUNT})', sentence, re.I)
                if value:
                    claims.append({'metric': min(matches)[1], 'value': value.group(1).strip(), 'citation': {
                                  'chunk_id': evidence['chunk_id'], 'page': evidence['page'], 'excerpt': sentence.strip()[:600]}, 'retrieval_score': evidence['score'], 'verified': False})
        unique = {}
        [unique.setdefault((c['metric'], c['value']), c) for c in claims]
        return {'claims': list(unique.values())}

    def verify(state):
        claims = [{**c, 'verified': c['value'] in c['citation']['excerpt']
                   and c['citation']['page'] > 0} for c in state.get('claims', [])]
        flags = list(state.get('quality_flags', []))
        if len([c for c in claims if c['verified']]) < 3:
            flags.append(
                'Fewer than three verified headline claims; human review required.')
        return {'claims': claims, 'quality_flags': flags}

    def summarize(state): return {'llm_summary': generate_grounded_summary(
        state.get('retrieved_evidence', []))}

    def finalize(state):
        status = 'needs_review' if state.get('quality_flags') else 'complete'
        # The UI renders these separately: values/tables, chart points, and prose. They
        # all retain the same evidence object, so a citation can be shown beside each.
        structured = [fact for fact in state.get(
            'financial_facts', []) if fact['validated']]
        charts = [c for c in structured if c['metric']
                  in ('revenue', 'ebitda', 'pat')]
        narratives = []
        for page in state.get('pages', []):
            if page.get('page_type') == 'text_native' and page.get('narrative_blocks'):
                narratives.append(
                    {'title': f"Source highlights - page {page['page']}", 'blocks': page['narrative_blocks'][:8], 'citation': {'page': page['page']}})
        result = {k: state.get(k) for k in ('document_id', 'claims', 'financial_facts',
                                            'quality_flags', 'research_plan', 'retrieved_evidence', 'llm_summary')}
        result.update({'structured_data': structured,
                      'chart_specs': charts, 'narrative_sections': narratives})
        store.save_run(state['run_id'], state['document_id'], status, result)
        return {'status': status, 'structured_data': structured, 'chart_specs': charts, 'narrative_sections': narratives}
    return ingest, chunk, plan, retrieve, extract, extract_financials, verify, summarize, finalize
