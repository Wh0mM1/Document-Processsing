"""Table/text to normalized, source-reconciled financial facts."""
import re

METRICS = {
    'revenue': r'(?:revenue|sales|total income)', 'ebitda': r'\bEBITDA\b', 'pat': r'(?:\bPAT\b|net profit|profit after tax)',
    'nii': r'(?:net interest income|\bNII\b)', 'deposits': r'\bdeposits?\b', 'advances': r'\badvances?\b', 'casa_ratio': r'\bCASA\b',
    'nim': r'\bNIM\b|net interest margin', 'gnpa': r'\bGNPA\b|gross NPA', 'nnpa': r'\bNNPA\b|net NPA',
    'cet1': r'\bCET1\b', 'capital_adequacy': r'(?:capital adequacy|\bCAR\b)', 'cost_to_income': r'cost.to.income'
}
VALUE = r'(?:₹|Rs\.?|INR|USD|\$)?\s?\d[\d,]*(?:\.\d+)?\s*(?:%|bps|crore|cr|mn|million|bn|billion)?'


def extract_facts(pages):
    facts = []
    seen = set()
    for page in pages:
        source = '\n'.join([page.get('text', ''), page.get('ocr_text', '')])
        for line in source.splitlines():
            line = ' '.join(line.split())
            for name, pattern in METRICS.items():
                match = re.search(pattern, line, re.I)
                if not match:
                    continue
                values = [v.strip() for v in re.findall(
                    VALUE, line, re.I) if re.search(r'\d', v)]
                if not values:
                    continue
                # prefer number after the metric, otherwise the closest numeric token.
                after = line[match.end():]
                value_match = re.search(VALUE, after, re.I)
                value = value_match.group(
                    0).strip() if value_match else values[0]
                normalized = value.replace(',', '').strip()
                meaningful = ('%' in value or any(unit in value.lower() for unit in (
                    '₹', 'rs', 'inr', 'usd', 'crore', 'cr', 'mn', 'million', 'bn', 'billion', 'bps')) or len(normalized) >= 3)
                if not meaningful:
                    continue
                key = (name, value, page['page'])
                if key in seen:
                    continue
                seen.add(key)
                facts.append({'metric': name, 'value': value, 'period': next(iter(re.findall(r'(?:Q[1-4]|H[12]|FY\d{2,4})', line, re.I)), None), 'citation': {
                             'page': page['page'], 'excerpt': line[:700]}, 'validated': value in source, 'source_type': 'ocr' if value in page.get('ocr_text', '') else 'native_text'})
    return facts
