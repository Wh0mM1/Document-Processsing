import argparse
import json
import uuid
from pathlib import Path
from .pipeline.graph import build_graph
from .output.report import render_report


def main():
    parser = argparse.ArgumentParser(description="FinSight AI Context-Driven Document Intelligence")
    parser.add_argument('source', help="Path to input PDF document")
    parser.add_argument('--output', default='data/latest-run.json', help="Destination path for JSON output")
    parser.add_argument('--pdf', default=None, help="Optional destination path for PDF report")
    args = parser.parse_args()

    run_id = str(uuid.uuid4())
    result = build_graph().invoke(
        {'source_path': args.source, 'run_id': run_id},
        {'configurable': {'thread_id': run_id}}
    )

    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2))

    pdf_dest = args.pdf or f"data/reports/{run_id}.pdf"
    render_report(result, pdf_dest)

    ctx = result.get('business_context', {})
    facts = result.get('validated_facts', [])
    charts = result.get('chart_specs', [])

    print(f"[{result['status'].upper()}] Successfully processed document:")
    print(f"  Company: {ctx.get('company')} ({ctx.get('sector')})")
    print(f"  Document Type: {ctx.get('document_type')} | Period: {ctx.get('period')}")
    print(f"  Validated Facts: {len(facts)} | Charts: {len(charts)}")
    print(f"  JSON output: {destination}")
    print(f"  PDF Report: {pdf_dest}")


if __name__ == '__main__':
    main()

