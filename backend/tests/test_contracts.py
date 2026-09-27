"""Provider and storage contracts: these mocks do not replace a real account smoke test."""
import json
from types import SimpleNamespace

import httpx
import pytest

from app.config import Settings
from app.models import Chunk, Document
from app.providers.openai_provider import OpenAIAnswers, OpenAIEmbeddings
from app.repositories.supabase import SupabaseRepository


def test_supabase_request_contract():
    calls = []
    document = Document(id='00000000-0000-0000-0000-000000000001', title='sample.pdf', created_at='2026-01-01')

    def handler(request):
        calls.append(request)
        assert request.headers['apikey'] == 'test-server-key'
        assert request.headers['authorization'] == 'Bearer test-server-key'
        if request.url.path == '/rest/v1/rpc/match_chunks':
            assert json.loads(request.content)['match_count'] == 6
            return httpx.Response(200, json=[{'id': 'chunk', 'document_id': document.id, 'title': 'sample.pdf',
                                             'page_number': 2, 'chunk_order': 1, 'text': 'Evidence', 'score': .9}])
        return httpx.Response(200, json=[])

    settings = Settings(_env_file=None, supabase_url='https://example.supabase.co', supabase_service_role_key='test-server-key')
    repository = SupabaseRepository(settings)
    repository.client.close()
    repository.client = httpx.Client(base_url=settings.supabase_url, transport=httpx.MockTransport(handler),
                                    headers={'apikey': 'test-server-key', 'Authorization': 'Bearer test-server-key'})
    repository.save_document(document)
    repository.save_pdf(document.id, b'%PDF-test')
    assert repository.search([0.1] * 1536, 6, .3)[0].page_number == 2
    repository.delete(document.id)
    assert [request.method for request in calls[-2:]] == ['DELETE', 'DELETE']
    assert '/storage/v1/object/' in calls[-2].url.path
    assert calls[-1].url.path == '/rest/v1/documents'
    assert json.loads(calls[-2].content)['prefixes'] == [f'{document.id}.pdf']
    repository.close()


def test_storage_failure_does_not_delete_metadata():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(503)
    repository = SupabaseRepository(Settings(_env_file=None, supabase_url='https://example.supabase.co'))
    repository.client.close()
    repository.client = httpx.Client(base_url='https://example.supabase.co', transport=httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPStatusError):
        repository.delete('test-id')
    assert len(calls) == 1
    repository.close()


def test_embedding_order_dimensions_and_cost():
    provider = OpenAIEmbeddings(Settings(_env_file=None, openai_api_key='test'))
    def embed(**kwargs):
        assert kwargs['dimensions'] == 1536
        return SimpleNamespace(data=[SimpleNamespace(index=1, embedding=[.2] * 1536),
                                     SimpleNamespace(index=0, embedding=[.1] * 1536)],
                               usage=SimpleNamespace(total_tokens=100))
    provider.client = SimpleNamespace(embeddings=SimpleNamespace(create=embed))
    vectors, cost = provider.embed(['first', 'second'])
    assert vectors[0][0] == .1 and len(vectors) == 2
    assert cost == pytest.approx(.000002)


def test_answer_only_receives_retrieved_chunks_and_handles_refusal():
    provider = OpenAIAnswers(Settings(_env_file=None, openai_api_key='test'))
    chunk = Chunk(id='retrieved-id', document_id='doc', title='sample.pdf', page_number=2,
                  chunk_order=0, text='Only this evidence reaches the model.')
    def parse(**kwargs):
        supplied = json.loads(kwargs['messages'][1]['content'])
        assert supplied == {'question': 'What evidence?', 'sources': [{'source_id': chunk.id, 'text': chunk.text}]}
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(parsed=None))],
                               usage=SimpleNamespace(prompt_tokens=100, completion_tokens=20))
    provider.client = SimpleNamespace(beta=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(parse=parse))))
    answer, cost = provider.answer('What evidence?', [chunk])
    assert answer.insufficient_evidence and not answer.claims
    assert cost == pytest.approx(.000072)


def test_live_configuration_rejects_unsafe_defaults():
    with pytest.raises(ValueError):
        Settings(_env_file=None, app_mode='live')
    with pytest.raises(ValueError):
        Settings(_env_file=None, cors_origins=['*'])
    with pytest.raises(ValueError):
        Settings(_env_file=None, app_mode='live', supabase_url='https://example.supabase.co',
                 supabase_service_role_key='test', openai_api_key='test', uploads_enabled=True)
