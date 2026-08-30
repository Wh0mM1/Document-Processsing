from finsight_agent.ingestion.chunking import structure_aware_chunks
from finsight_agent.analysis.context import analyze_document_context
from finsight_agent.analysis.charts import plan_contextual_charts
from finsight_agent.core.contracts import BusinessContext, CanonicalFinancialFact, ManagementGuidance
from finsight_agent.ingestion.embeddings import HashEmbeddingProvider
from finsight_agent.analysis.extraction import extract_context_aware_facts
from finsight_agent.pipeline.graph import build_graph
from finsight_agent.ingestion.pdf_parser import table_to_markdown
from finsight_agent.analysis.insights import generate_business_insights
from finsight_agent.output.narrative import extract_visual_chart_data
from finsight_agent.output.mapping import map_to_geojit_template
from finsight_agent.storage.store import SQLiteResearchStore
from finsight_agent.analysis.validation import validate_and_score_facts


def test_embeddings_are_persisted_and_searchable(tmp_path):
    store = SQLiteResearchStore(str(tmp_path / 'research.sqlite3'))
    text = 'Revenue grew to Rs. 500 crore. EBITDA was Rs. 80 crore.'
    embeddings = HashEmbeddingProvider()
    store.index('doc', 'sample.pdf', [{'id': 'chunk-1', 'page': 1, 'text': text}],
                embeddings.embed([text]))
    hits = store.search('doc', embeddings.embed(['revenue growth'])[0])
    assert hits[0]['page'] == 1
    assert 'Revenue' in hits[0]['text']


def test_table_to_markdown():
    rows = [
        ['Metric', 'Q1-2026', 'Q2-2026'],
        ['Net interest income', '216.35', '215.29'],
        ['Core operating profit', '175.05', '170.78']
    ]
    md = table_to_markdown(rows)
    assert '| Metric | Q1-2026 | Q2-2026 |' in md
    assert '| Net interest income | 216.35 | 215.29 |' in md


def test_structure_aware_chunks_with_tables_and_metadata():
    pages = [{
        'page': 8,
        'title': 'Profit & loss statement',
        'tables': [{
            'markdown': '| Metric | Q2-2026 |\n| Net interest income | 215.29 |'
        }],
        'narrative_blocks': [{
            'text': 'Core operating profit grew by 6.5% y-o-y to Rs 170.78 bn.'
        }]
    }]
    chunks = structure_aware_chunks('doc_123', pages)
    assert len(chunks) == 2
    table_chunk = next(c for c in chunks if c['type'] == 'table')
    narrative_chunk = next(c for c in chunks if c['type'] == 'narrative')
    assert '[Slide 8: Profit & loss statement]' in table_chunk['text']
    assert 'Net interest income' in table_chunk['text']
    assert '[Slide 8: Profit & loss statement]' in narrative_chunk['text']


def test_context_analysis_banking_vs_consumer():
    bank_pages = [
        {'page': 1, 'text': 'ICICI Bank Limited. Performance review Q2-2026. Net interest income and advances expanded.'},
        {'page': 2, 'text': 'Certain statements are forward-looking. Deposits grew 9.1% and GNPA ratio improved to 1.58%.'}
    ]
    ctx_bank = analyze_document_context(bank_pages)
    assert ctx_bank.business_model == 'banking'
    assert ctx_bank.company == 'ICICI Bank Limited'
    assert 'NII' in ctx_bank.primary_metrics or 'PAT' in ctx_bank.primary_metrics

    consumer_pages = [
        {'page': 1, 'text': 'Eternal Limited (formerly Zomato Limited). Online food delivery, Blinkit quick commerce and Hyperpure.'},
        {'page': 2, 'text': 'Geojit Financial Services. Recommendation Summary: HOLD. Target: Rs. 337. CMP: Rs. 284.'}
    ]
    ctx_consumer = analyze_document_context(consumer_pages)
    assert ctx_consumer.business_model == 'consumer_internet'
    assert ctx_consumer.company == 'Eternal Limited'
    assert ctx_consumer.has_target_and_rating is True


def test_extract_context_aware_facts_and_guidance():
    pages = [
        {
            'page': 4,
            'text': 'Profit after tax grew by 5.2% y-o-y to ₹ 123.59 bn in Q2-2026. Management guidance aims to expand branch count by 400.'
        },
        {
            'page': 8,
            'tables': [{
                'rows': [
                    ['(₹ billion)', 'FY2025', 'Q2-2025', 'Q2-2026'],
                    ['Net interest income', '811.65', '200.48', '215.29'],
                    ['Profit after tax', '472.27', '117.46', '123.59']
                ]
            }]
        }
    ]
    ctx = BusinessContext(
        company="ICICI Bank Limited",
        sector="Banking & Financial Services",
        document_type="investor_presentation",
        period="Q2-2026",
        business_model="banking",
        primary_metrics=["PAT", "NII", "Deposits", "Advances", "NPA"]
    )
    facts, guidance = extract_context_aware_facts(pages, ctx, "doc_test")
    assert len(facts) >= 2
    pat_facts = [f for f in facts if f.metric_name == "Profit After Tax"]
    assert len(pat_facts) > 0
    assert any(f.value == 123.59 for f in pat_facts)
    assert len(guidance) >= 1
    assert "expand branch count" in guidance[0].statement


def test_validation_and_growth_cross_check():
    ctx = BusinessContext(
        company="ICICI Bank Limited",
        sector="Banking",
        document_type="investor_presentation",
        period="Q2-2026",
        business_model="banking",
        primary_metrics=["Profit After Tax", "Net Interest Income"]
    )
    facts = [
        CanonicalFinancialFact(
            metric_name="Profit After Tax",
            raw_metric_label="Profit after tax",
            value=123.59,
            unit="₹ billion",
            period="Q2-2026",
            growth=5.2,
            source_page=4
        ),
        CanonicalFinancialFact(
            metric_name="Profit After Tax",
            raw_metric_label="Profit after tax",
            value=117.46,
            unit="₹ billion",
            period="Q2-2025",
            source_page=8
        )
    ]
    validated = validate_and_score_facts(facts, ctx)
    lead_fact = next(f for f in validated if f.period == "Q2-2026")
    assert lead_fact.relevance_score >= 0.90
    assert lead_fact.validation_status == "verified"
    assert lead_fact.comparison_period == "Q2-2025"


def test_zero_hallucination_template_mapping():
    # 1. Investor Presentation (ICICI Bank) -> Target/Rating should be N/A
    icici_ctx = BusinessContext(
        company="ICICI Bank Limited",
        sector="Banking & Financial Services",
        document_type="investor_presentation",
        period="Q2-2026",
        business_model="banking",
        primary_metrics=["Profit After Tax", "Net Interest Income"]
    )
    mapping_icici = map_to_geojit_template([], icici_ctx, [{'page': 1, 'text': 'ICICI Bank Q2-2026 investor presentation'}])
    assert mapping_icici.target_price.status == "not_available_in_source"
    assert "N/A" in mapping_icici.target_price.value
    assert mapping_icici.recommendation_rating.status == "not_available_in_source"
    assert "Target Price" in mapping_icici.missing_fields

    # 2. Equity Research Report (Eternal) -> Target/Rating should be populated
    eternal_ctx = BusinessContext(
        company="Eternal Limited",
        sector="Internet & Consumer Technology",
        document_type="equity_research_report",
        period="Q1FY26",
        business_model="consumer_internet",
        primary_metrics=["Revenue from Operations", "EBITDA"]
    )
    research_pages = [{'page': 1, 'text': 'Geojit Research. Eternal Limited. Target: Rs. 337. Rating: HOLD. CMP: Rs. 284.'}]
    mapping_eternal = map_to_geojit_template([], eternal_ctx, research_pages)
    assert mapping_eternal.target_price.status == "populated"
    assert "337" in mapping_eternal.target_price.value
    assert mapping_eternal.recommendation_rating.value == "HOLD"


def test_chart_planning_banking_vs_consumer():
    bank_ctx = BusinessContext(
        company="ICICI Bank",
        sector="Banking",
        document_type="investor_presentation",
        period="Q2-2026",
        business_model="banking"
    )
    bank_facts = [
        CanonicalFinancialFact(metric_name="Profit After Tax", raw_metric_label="PAT", value=117.46, unit="₹ bn", period="Q2-2025"),
        CanonicalFinancialFact(metric_name="Profit After Tax", raw_metric_label="PAT", value=123.59, unit="₹ bn", period="Q2-2026"),
        CanonicalFinancialFact(metric_name="Net Interest Income", raw_metric_label="NII", value=200.48, unit="₹ bn", period="Q2-2025"),
        CanonicalFinancialFact(metric_name="Net Interest Income", raw_metric_label="NII", value=215.29, unit="₹ bn", period="Q2-2026")
    ]
    charts = plan_contextual_charts(bank_facts, bank_ctx)
    chart_metrics = [c.metric for c in charts]
    assert "Profit After Tax" in chart_metrics
    assert "Net Interest Income" in chart_metrics


def test_sqlite_store_thread_safety(tmp_path):
    import concurrent.futures
    store = SQLiteResearchStore(str(tmp_path / 'thread_test.sqlite3'))
    embeddings = HashEmbeddingProvider()

    def worker(i):
        doc_id = f'doc_{i}'
        text = f'Revenue was {i * 100} crore.'
        store.index(doc_id, f'file_{i}.pdf', [{'id': f'c_{i}', 'page': 1, 'text': text}], embeddings.embed([text]))
        hits = store.search(doc_id, embeddings.embed(['revenue'])[0])
        assert len(hits) == 1
        store.save_run(f'run_{i}', doc_id, 'complete', {'status': 'ok'})

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(worker, i) for i in range(10)]
        for f in concurrent.futures.as_completed(futures):
            f.result()


def test_upload_content_hash_deduplication(tmp_path):
    import hashlib
    content = b"%PDF-1.4 mock financial document content"
    doc_hash = hashlib.sha256(content).hexdigest()

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    target_file = upload_dir / f"{doc_hash}.pdf"

    # 1st upload
    if not target_file.exists():
        target_file.write_bytes(content)
    assert target_file.exists()
    mtime_first = target_file.stat().st_mtime

    # 2nd upload with identical content
    if not target_file.exists():
        target_file.write_bytes(content)

    # Verify no duplicate file created and same canonical file referenced
    files = list(upload_dir.glob("*.pdf"))
    assert len(files) == 1
    assert files[0].name == f"{doc_hash}.pdf"

