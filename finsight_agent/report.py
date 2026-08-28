from pathlib import Path
from html import escape
GROUPS = {'Earnings & profitability': {'revenue', 'ebitda', 'pat', 'nii', 'nim', 'cost_to_income'}, 'Balance sheet & growth': {
    'deposits', 'advances', 'casa_ratio'}, 'Asset quality & capital': {'gnpa', 'nnpa', 'cet1', 'capital_adequacy'}}


def render_report(result, destination):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib import colors
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    story = [Paragraph('FinSight AI Research Report', styles['Title']), Paragraph(
        f"Source document: {result['document_id']}", styles['Normal']), Spacer(1, 14)]
    summary = result.get('llm_summary', {})
    if summary.get('mode') == 'llm' and summary.get('text'):
        story += [Paragraph('Executive summary', styles['Heading2']),
                  Paragraph(escape(summary['text']), styles['BodyText']), Spacer(1, 12)]
    facts = result.get('structured_data', [])
    for title, metrics in GROUPS.items():
        rows = [['Metric', 'Value', 'Period', 'Source page']]+[[item['metric'].replace('_', ' ').upper(), item['value'], item.get(
            'period') or '-', str(item['citation']['page'])] for item in facts if item['metric'] in metrics]
        if len(rows) > 1:
            table = Table(rows, colWidths=[155, 130, 100, 80])
            table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#163020')), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white), ('GRID',
                           (0, 0), (-1, -1), .3, colors.HexColor('#9aa69b')), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('PADDING', (0, 0), (-1, -1), 6)]))
            story += [Paragraph(title, styles['Heading2']),
                      table, Spacer(1, 12)]
    if result.get('narrative_sections'):
        story += [PageBreak(), Paragraph('Source-grounded narrative',
                                         styles['Heading1'])]
        for section in result['narrative_sections']:
            story.append(Paragraph(section['title'], styles['Heading3']))
            for block in section['blocks']:
                story.append(Paragraph(
                    f"- {escape(block['text'])} (p. {block['source_page']})", styles['BodyText']))
            story.append(Spacer(1, 8))
    story += [PageBreak(), Paragraph('Citation appendix', styles['Heading1'])]
    for item in facts:
        story.append(Paragraph(
            f"<b>{escape(item['metric'].upper())} - {escape(item['value'])}</b> (page {item['citation']['page']}): {escape(item['citation']['excerpt'])}", styles['BodyText']))
    SimpleDocTemplate(str(output), pagesize=A4, rightMargin=40,
                      leftMargin=40, topMargin=38, bottomMargin=38).build(story)
    return str(output)
