from io import BytesIO
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen.canvas import Canvas

from app.config import Settings
from app.main import create_app
from app.models import Claim, ModelAnswer
from app.services.extraction import chunk_pages


def make_pdf(pages):
    stream = BytesIO()
    pdf = Canvas(stream)
    for text in pages:
        pdf.drawString(50, 750, text)
        pdf.showPage()
    pdf.save()
    return stream.getvalue()


@pytest.fixture
def client(tmp_path):
    settings = Settings(_env_file=None, local_data_dir=tmp_path, questions_per_minute=100,
                        uploads_per_hour=100, requests_per_minute=500)
    with TestClient(create_app(settings)) as connection:
        yield connection


def upload(client, content=None):
    return client.post('/api/documents', files={'file': ('sample.pdf', content or make_pdf([
        'The project budget is 1200 credits.', 'Raw coded observations are retained for 90 days, then deleted.'
    ]), 'application/pdf')})


def test_upload_question_citation_and_delete(client):
    response = upload(client)
    assert response.status_code == 201
    document = response.json()
    assert document['status'] == 'ready' and document['page_count'] == 2
    answer = client.post('/api/questions', json={'question': 'How long are raw coded observations retained?'}).json()
    assert not answer['abstained'] and '90 days' in answer['answer']
    citation = answer['citations'][0]
    assert citation['document_id'] == document['id'] and citation['page_number'] == 2
    pdf = client.get(f'/api/documents/{document["id"]}/pdf')
    assert pdf.headers['cache-control'] == 'no-store'
    assert '90 days' in PdfReader(BytesIO(pdf.content)).pages[citation['page_number'] - 1].extract_text()
    assert client.delete(f'/api/documents/{document["id"]}').status_code == 204
    assert client.get('/api/documents').json() == []
    assert client.get(f'/api/documents/{document["id"]}/pdf').status_code == 404
    assert client.post('/api/questions', json={'question': 'What is the project budget?'}).json()['abstained']
    assert client.delete(f'/api/documents/{document["id"]}').status_code == 204


@pytest.mark.parametrize('filename,kind,data,status', [
    ('notes.txt', 'text/plain', b'hello', 415),
    ('fake.pdf', 'application/pdf', b'not a PDF', 400),
    ('broken.pdf', 'application/pdf', b'%PDF-1.7 broken', 400),
])
def test_bad_files(client, filename, kind, data, status):
    response = client.post('/api/documents', files={'file': (filename, data, kind)})
    assert response.status_code == status
    assert 'detail' in response.json()


def test_scan_without_text(client):
    pdf = PdfWriter()
    pdf.add_blank_page(width=595, height=842)
    stream = BytesIO()
    pdf.write(stream)
    response = upload(client, stream.getvalue())
    assert response.status_code == 400 and 'OCR' in response.json()['detail']
    assert client.get('/api/documents').json()[0]['status'] == 'error'


def test_encrypted_pdf(client):
    writer = PdfWriter(PdfReader(BytesIO(make_pdf(['secret']))))
    writer.encrypt('test-password')
    stream = BytesIO()
    writer.write(stream)
    response = upload(client, stream.getvalue())
    assert response.status_code == 400 and 'Password' in response.json()['detail']


def test_file_and_page_limits(tmp_path):
    settings = Settings(_env_file=None, local_data_dir=tmp_path, max_file_mb=1, max_pages=1)
    with TestClient(create_app(settings)) as client:
        assert upload(client, b'%PDF-' + b'x' * (1024 * 1024)).status_code == 413
        assert upload(client).status_code == 400


def test_page_boundaries_and_overlap():
    chunks = chunk_pages('id', 'title', [(1, 'alpha ' * 600), (2, 'omega ' * 600)])
    assert all('omega' not in item.text for item in chunks if item.page_number == 1)
    assert [item.chunk_order for item in chunks] == list(range(len(chunks)))
    assert chunks[0].text[-200:] == chunks[1].text[:200]
    assert len({item.id for item in chunks}) == len(chunks)


def test_missing_evidence(client):
    upload(client)
    result = client.post('/api/questions', json={'question': 'Who won the lunar football championship?'}).json()
    assert result['abstained'] and result['citations'] == []


def test_invented_citation_fails_closed(client):
    upload(client)
    class InventedSource:
        def answer(self, question, chunks):
            return ModelAnswer(insufficient_evidence=False, claims=[Claim(text='Invented', source_ids=['not-retrieved'])]), 0
    client.app.state.service.answers = InventedSource()
    result = client.post('/api/questions', json={'question': 'What is the project budget?'}).json()
    assert result['abstained'] and not result['citations']


def test_auth_and_disabled_mutations(tmp_path):
    settings = Settings(_env_file=None, local_data_dir=tmp_path, demo_access_token='test-token', uploads_enabled=False, deletes_enabled=False)
    with TestClient(create_app(settings)) as client:
        assert client.get('/api/documents').status_code == 401
        client.headers['Authorization'] = 'Bearer test-token'
        assert client.get('/api/documents').status_code == 200
        assert upload(client).status_code == 403
        assert client.delete('/api/documents/00000000-0000-0000-0000-000000000000').status_code == 403


def test_validation_and_cors(client):
    for question in [' ', 'x' * 1501]:
        assert client.post('/api/questions', json={'question': question}).status_code == 422
    assert client.get('/api/documents/not-a-uuid/pdf').status_code == 422
    allowed = client.options('/api/questions', headers={'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'POST'})
    blocked = client.options('/api/questions', headers={'Origin': 'https://untrusted.example', 'Access-Control-Request-Method': 'POST'})
    assert allowed.headers['access-control-allow-origin'] == 'http://localhost:5173'
    assert 'access-control-allow-origin' not in blocked.headers


def test_rate_limit(tmp_path):
    settings = Settings(_env_file=None, local_data_dir=tmp_path, questions_per_minute=1)
    with TestClient(create_app(settings)) as client:
        assert client.post('/api/questions', json={'question': 'Any evidence?'}).status_code == 200
        assert client.post('/api/questions', json={'question': 'Any evidence?'}).status_code == 429


def test_restart_marks_interrupted_upload(tmp_path):
    from app.models import Document
    from app.repositories.local import LocalRepository
    repository = LocalRepository(tmp_path)
    repository.save_document(Document(id='interrupted', title='sample.pdf', created_at='2026-01-01', status='embedding'))
    with TestClient(create_app(Settings(_env_file=None, local_data_dir=tmp_path))) as client:
        assert client.get('/api/documents').json()[0]['status'] == 'error'


def test_no_uncited_claims(client):
    upload(client)
    class NoSources:
        def answer(self, question, chunks):
            return ModelAnswer(insufficient_evidence=False, claims=[Claim(text='Unsupported', source_ids=[])]), 0
    client.app.state.service.answers = NoSources()
    assert client.post('/api/questions', json={'question': 'What is the project budget?'}).json()['abstained']


def test_streamed_body_limit_without_content_length(client):
    # A client can omit Content-Length; the receive wrapper must still cap bytes.
    response = client.post('/api/questions', content=iter([b'{"question":"', b'x' * 20_000, b'"}']),
                           headers={'Content-Type': 'application/json'})
    assert response.status_code == 413


def test_failed_embedding_never_enters_search(client):
    class BrokenEmbeddings:
        def embed(self, texts):
            raise RuntimeError('A provider error containing a pretend-secret')
    client.app.state.service.embeddings = BrokenEmbeddings()
    response = upload(client)
    assert response.status_code == 400
    assert 'pretend-secret' not in response.text
    assert client.get('/api/documents').json()[0]['status'] == 'error'


def test_library_capacity(tmp_path):
    with TestClient(create_app(Settings(_env_file=None, local_data_dir=tmp_path, max_documents=1))) as client:
        assert upload(client).status_code == 201
        assert upload(client).status_code == 400
        assert len(client.get('/api/documents').json()) == 1
