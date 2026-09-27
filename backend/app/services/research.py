from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4
import logging

from app.models import Answer, Citation, Document
from app.providers.interfaces import AnswerProvider, EmbeddingProvider
from app.repositories.base import Repository
from app.services.extraction import DocumentError, chunk_pages, extract_pages

ABSTENTION = 'The uploaded documents do not contain enough information to answer this question.'
logger = logging.getLogger(__name__)


class ResearchService:
    def __init__(self, settings, repository: Repository, embeddings: EmbeddingProvider, answers: AnswerProvider):
        self.settings, self.repository = settings, repository
        self.embeddings, self.answers = embeddings, answers

    def upload(self, title: str, content: bytes):
        if len(self.repository.list_documents()) >= self.settings.max_documents:
            raise DocumentError('This demo library is full. Delete a document before uploading another.')
        document = Document(id=str(uuid4()), title=title, created_at=datetime.now(timezone.utc).isoformat())
        self.repository.save_document(document)
        try:
            pages = extract_pages(content, self.settings.max_pages)
            chunks = chunk_pages(document.id, title, pages)
            document.page_count = len(pages)
            document.chunk_count = len(chunks)
            document.status = 'embedding'
            self.repository.save_document(document)
            vectors, cost = self.embeddings.embed([chunk.text for chunk in chunks])
            if len(vectors) != len(chunks):
                raise ValueError('Missing embeddings')
            for chunk, vector in zip(chunks, vectors):
                chunk.embedding = vector
            self.repository.save_pdf(document.id, content)
            self.repository.save_chunks(chunks)
            document.status = 'ready'
            document.estimated_cost_usd = cost
            self.repository.save_document(document)
            return document
        except Exception as exc:
            document.status = 'error'
            document.error = str(exc) if isinstance(exc, DocumentError) else 'Processing failed. Delete this document and try again.'
            self.repository.save_document(document)
            if isinstance(exc, DocumentError):
                raise
            logger.error('Upload processing failed: %s', type(exc).__name__)
            raise DocumentError(document.error) from exc

    def ask(self, question):
        started = perf_counter()
        vectors, embedding_cost = self.embeddings.embed([question])
        threshold = 0.06 if self.settings.app_mode == 'local' else self.settings.similarity_threshold
        chunks = self.repository.search(vectors[0], 6, threshold)
        cost, claims = embedding_cost, []
        source_map = {item.id: item for item in chunks}
        if chunks:
            result, answer_cost = self.answers.answer(question, chunks)
            cost += answer_cost
            # Fail closed: even one invented or missing source invalidates the response.
            valid = all(claim.text.strip() and claim.source_ids and
                        all(source_id in source_map for source_id in claim.source_ids) for claim in result.claims)
            if not result.insufficient_evidence and valid:
                claims = result.claims
        citations = []
        used = set()
        for claim in claims:
            for source_id in claim.source_ids:
                if source_id not in used:
                    item = source_map[source_id]
                    citations.append(Citation(id=item.id, document_id=item.document_id, title=item.title,
                                               page_number=item.page_number, excerpt=item.text))
                    used.add(source_id)
        is_ai = bool(self.settings.openai_api_key and (getattr(self.settings, 'answer_provider', '') == 'openai' or getattr(self.settings, 'openai_base_url', '')))
        return Answer(answer='\n\n'.join(claim.text for claim in claims) if claims else ABSTENTION,
                      claims=claims, citations=citations, abstained=not claims,
                      latency_ms=round((perf_counter() - started) * 1000), estimated_cost_usd=cost,
                      mode='ai' if is_ai else self.settings.app_mode)
