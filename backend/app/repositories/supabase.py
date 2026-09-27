"""Explicit HTTP calls keep the PostgREST and Storage contract visible to learners."""
import httpx
from app.models import Chunk, Document


class SupabaseRepository:
    def __init__(self, settings):
        self.bucket = settings.storage_bucket
        self.client = httpx.Client(base_url=settings.supabase_url.rstrip('/'), timeout=45,
                                   headers={'apikey': settings.supabase_service_role_key,
                                            'Authorization': f'Bearer {settings.supabase_service_role_key}'})

    def request(self, method, path, **kwargs):
        response = self.client.request(method, path, **kwargs)
        response.raise_for_status()
        return response

    def list_documents(self):
        rows = self.request('GET', '/rest/v1/documents', params={'select': '*', 'order': 'created_at.desc'}).json()
        return [Document.model_validate(row) for row in rows]

    def get_document(self, document_id):
        rows = self.request('GET', '/rest/v1/documents', params={'id': f'eq.{document_id}', 'select': '*'}).json()
        return Document.model_validate(rows[0]) if rows else None

    def save_document(self, document):
        self.request('POST', '/rest/v1/documents', json=document.model_dump(),
                     headers={'Prefer': 'resolution=merge-duplicates'})

    def object_path(self, document_id):
        # IDs come from server-generated UUIDs, never user filenames.
        return f'/storage/v1/object/{self.bucket}/{document_id}.pdf'

    def save_pdf(self, document_id, content):
        self.request('POST', self.object_path(document_id), content=content,
                     headers={'Content-Type': 'application/pdf'})

    def read_pdf(self, document_id):
        return self.request('GET', self.object_path(document_id)).content

    def save_chunks(self, chunks):
        for start in range(0, len(chunks), 50):
            self.request('POST', '/rest/v1/chunks',
                         json=[item.model_dump(exclude={'score'}) for item in chunks[start:start + 50]])

    def search(self, vector, limit, threshold):
        rows = self.request('POST', '/rest/v1/rpc/match_chunks',
                            json={'query_embedding': vector, 'match_count': limit, 'match_threshold': threshold}).json()
        return [Chunk.model_validate(row) for row in rows]

    def delete(self, document_id):
        # Hide the document before deleting bytes. If either operation fails, a retry is safe.
        # Storage's bulk removal is idempotent, including an already missing object.
        self.request('DELETE', f'/storage/v1/object/{self.bucket}', json={'prefixes': [f'{document_id}.pdf']})
        self.request('DELETE', '/rest/v1/documents', params={'id': f'eq.{document_id}'})

    def close(self):
        self.client.close()
