"""Offline regression by default. --api-url evaluates an already seeded live library."""
import argparse
from io import BytesIO
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time

import httpx
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))


def normalized(text):
    return ' '.join(text.lower().split())


def score(case, result, source_text):
    expected_abstention = case.get('abstain', False)
    answered = not result['abstained']
    expected_sources = {tuple(source) for source in case['sources']}
    valid_citations = []
    for citation in result['citations']:
        key = (citation['title'], citation['page_number'])
        actual_page = source_text.get(key, '')
        valid_citations.append(key in expected_sources and normalized(citation['excerpt']) in normalized(actual_page))
    keyword_match = all(any(word.lower() in result['answer'].lower() for word in group)
                        for group in case.get('expected', []))
    returned_sources = {(item['title'], item['page_number']) for item in result['citations']}
    return {
        'answer_correct': (not answered) if expected_abstention else answered and keyword_match,
        'abstention_correct': result['abstained'] == expected_abstention,
        'citation_precision': sum(valid_citations) / len(valid_citations) if valid_citations else None,
        'source_recall': len(expected_sources & returned_sources) / len(expected_sources) if expected_sources else None,
        'valid_citations': sum(valid_citations), 'citation_count': len(valid_citations),
    }


def evaluate(client, delay):
    cases = json.loads((ROOT / 'evaluation/questions.json').read_text())
    documents = client.get('/api/documents')
    documents.raise_for_status()
    source_text = {}
    for document in documents.json():
        if document['status'] != 'ready':
            continue
        response = client.get(f'/api/documents/{document["id"]}/pdf')
        response.raise_for_status()
        for number, page in enumerate(PdfReader(BytesIO(response.content)).pages, 1):
            source_text[(document['title'], number)] = page.extract_text() or ''
    rows = []
    for case in cases:
        started = time.perf_counter()
        try:
            response = client.post('/api/questions', json={'question': case['question']})
            response.raise_for_status()
            result = response.json()
            rows.append({'id': case['id'], 'question': case['question'], 'expected_abstention': case.get('abstain', False),
                         **score(case, result, source_text), 'latency_ms': round((time.perf_counter() - started) * 1000),
                         'estimated_cost_usd': result['estimated_cost_usd'], 'response': result})
        except Exception as exc:
            rows.append({'id': case['id'], 'error': type(exc).__name__, 'answer_correct': False, 'abstention_correct': False})
        if delay:
            time.sleep(delay)
    successful = [row for row in rows if 'error' not in row]
    abstentions = [row for row in rows if row.get('expected_abstention')]
    answerable = [row for row in rows if not row.get('expected_abstention') and 'error' not in row]
    citation_count = sum(row.get('citation_count', 0) for row in rows)
    latency = sorted(row['latency_ms'] for row in successful)
    summary = {
        'questions': len(rows), 'request_errors': len(rows) - len(successful),
        'answer_correctness_heuristic': sum(row['answer_correct'] for row in rows) / len(rows),
        'citation_precision_heuristic': sum(row.get('valid_citations', 0) for row in rows) / citation_count if citation_count else None,
        'mean_expected_source_recall': statistics.mean(row['source_recall'] for row in answerable) if answerable else None,
        'abstention_accuracy': sum(row['abstention_correct'] for row in rows) / len(rows),
        'unanswerable_abstention_rate': statistics.mean(row['abstention_correct'] for row in abstentions) if abstentions else None,
        'false_abstention_rate': statistics.mean(row['response']['abstained'] for row in answerable) if answerable else None,
        'latency_p50_ms': statistics.median(latency) if latency else None,
        'latency_p95_ms': latency[min(len(latency) - 1, int(len(latency) * .95))] if latency else None,
        'estimated_question_cost_usd': sum(row.get('estimated_cost_usd', 0) for row in rows),
    }
    return {'summary': summary, 'cases': rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--api-url', help='Already running API containing the three sample PDFs. This can incur model costs.')
    parser.add_argument('--delay', type=float, default=6.2, help='Seconds between live API questions; respects 10/minute limit.')
    parser.add_argument('--output', default=str(ROOT / 'evaluation/results.json'))
    args = parser.parse_args()
    if args.api_url:
        token = os.environ.get('DEMO_ACCESS_TOKEN', '')
        with httpx.Client(base_url=args.api_url, timeout=180, headers={'Authorization': f'Bearer {token}'}) as client:
            report = evaluate(client, args.delay)
        report['mode'] = 'external-api'
    else:
        from fastapi.testclient import TestClient
        from app.config import Settings
        from app.main import create_app
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(_env_file=None, app_mode='local', local_data_dir=Path(directory),
                                questions_per_minute=100, requests_per_minute=500)
            with TestClient(create_app(settings)) as client:
                for path in sorted((ROOT / 'sample_documents').glob('*.pdf')):
                    response = client.post('/api/documents', files={'file': (path.name, path.read_bytes(), 'application/pdf')})
                    response.raise_for_status()
                report = evaluate(client, 0)
        report['mode'] = 'offline-demonstration'
    Path(args.output).write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report['summary'], indent=2))


if __name__ == '__main__':
    main()
