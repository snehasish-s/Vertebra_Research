from contextlib import asynccontextmanager
import logging
from threading import BoundedSemaphore
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from app.config import Settings
from app.models import Answer, Document, Question
from app.providers.local import LocalAnswers, LocalEmbeddings
from app.repositories.local import LocalRepository
from app.security import BodyLimitMiddleware, RequestLimiter, authorize
from app.services.extraction import DocumentError
from app.services.research import ResearchService


def create_app(settings=None, repository=None, embeddings=None, answers=None):
    settings = settings or Settings()
    if settings.app_mode == 'live':
        from app.providers.openai_provider import OpenAIAnswers, OpenAIEmbeddings
        from app.repositories.supabase import SupabaseRepository
        repository = repository or SupabaseRepository(settings)
        embeddings, answers = embeddings or OpenAIEmbeddings(settings), answers or OpenAIAnswers(settings)
    else:
        repository = repository or LocalRepository(settings.local_data_dir)
        embeddings = embeddings or LocalEmbeddings()
        if (settings.answer_provider == 'openai' or (settings.openai_base_url and settings.openai_api_key)) and answers is None:
            from app.providers.openai_provider import OpenAIAnswers
            answers = OpenAIAnswers(settings)
        else:
            answers = answers or LocalAnswers()
    service = ResearchService(settings, repository, embeddings, answers)
    mutations = BoundedSemaphore(1)
    questions = BoundedSemaphore(2)

    @asynccontextmanager
    async def lifespan(app):
        # Single-worker deployment: an interrupted upload is never silently shown as ready.
        for document in await run_in_threadpool(repository.list_documents):
            if document.status in ('extracting', 'embedding'):
                document.status = 'error'
                document.error = 'Processing was interrupted. Delete this document and upload it again.'
                await run_in_threadpool(repository.save_document, document)
        yield
        if hasattr(repository, 'close'):
            repository.close()

    app = FastAPI(title='Vertebra Research', version='1.0.0', lifespan=lifespan,
                  docs_url='/docs' if settings.app_mode == 'local' else None, redoc_url=None,
                  openapi_url='/openapi.json' if settings.app_mode == 'local' else None)
    app.state.settings = settings
    app.state.limiter = RequestLimiter()
    app.state.service = service
    app.add_middleware(BodyLimitMiddleware, maximum=settings.max_file_mb * 1024 * 1024 + 65_536)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                       allow_methods=['GET', 'POST', 'DELETE'], allow_headers=['Authorization', 'Content-Type'])

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse({'detail': 'Check your input: use a valid document ID, PDF file, or question of 3–1500 characters.'}, 422)

    @app.exception_handler(Exception)
    async def unexpected_error(request, exc):
        logging.getLogger(__name__).error('Request failed: %s', type(exc).__name__)
        return JSONResponse({'detail': 'The research service is temporarily unavailable. Please try again.'}, 503)

    @app.get('/')
    def root():
        return {
            'name': 'Vertebra Research API',
            'status': 'online',
            'mode': settings.app_mode,
            'web_ui': 'http://127.0.0.1:5173',
            'docs': '/docs' if settings.app_mode == 'local' else None,
            'health': '/health',
            'message': 'FastAPI backend is running. Open http://127.0.0.1:5173 in your browser for the research assistant interface.'
        }

    @app.get('/health')
    def health():
        return {'status': 'ok', 'mode': settings.app_mode}

    @app.get('/api/config')
    def public_config():
        is_ai = bool(settings.openai_api_key and (getattr(settings, 'answer_provider', '') == 'openai' or getattr(settings, 'openai_base_url', '')))
        return {'mode': 'ai' if is_ai else settings.app_mode, 'uploads_enabled': settings.uploads_enabled,
                'deletes_enabled': settings.deletes_enabled, 'access_required': bool(settings.demo_access_token),
                'max_file_mb': settings.max_file_mb, 'max_pages': settings.max_pages,
                'ai_model': settings.answer_model if is_ai else None}

    @app.get('/api/documents', response_model=list[Document], dependencies=[Depends(authorize)])
    def documents():
        return repository.list_documents()

    @app.post('/api/documents', response_model=Document, dependencies=[Depends(authorize)], status_code=201)
    async def upload(file: UploadFile):
        if not settings.uploads_enabled:
            raise HTTPException(403, 'Uploads are disabled for this demo.')
        if not mutations.acquire(blocking=False):
            raise HTTPException(409, 'Another document is being processed. Please try again shortly.')
        try:
            title = (file.filename or '').replace('\\', '/').split('/')[-1].strip()
            if not title.lower().endswith('.pdf') or file.content_type not in ('application/pdf', 'application/octet-stream'):
                raise HTTPException(415, 'Only PDF files are supported.')
            if len(title) > 180:
                raise HTTPException(400, 'Please shorten the file name to fewer than 180 characters.')
            content = await file.read(settings.max_file_mb * 1024 * 1024 + 1)
            if len(content) > settings.max_file_mb * 1024 * 1024:
                raise HTTPException(413, f'Please use a PDF smaller than {settings.max_file_mb} MB.')
            return await run_in_threadpool(service.upload, title, content)
        except DocumentError as exc:
            raise HTTPException(400, str(exc)) from exc
        finally:
            await file.close()
            mutations.release()

    @app.post('/api/questions', response_model=Answer, dependencies=[Depends(authorize)])
    def ask(payload: Question):
        if not questions.acquire(blocking=False):
            raise HTTPException(429, 'Two questions are already running. Please try again shortly.')
        try:
            return service.ask(payload.question)
        finally:
            questions.release()

    @app.get('/api/documents/{document_id}/pdf', dependencies=[Depends(authorize)])
    def pdf(document_id: UUID):
        document = repository.get_document(str(document_id))
        if not document or document.status != 'ready':
            raise HTTPException(404, 'This document is no longer available.')
        return Response(repository.read_pdf(str(document_id)), media_type='application/pdf',
                        headers={'Cache-Control': 'no-store', 'Content-Disposition': 'inline; filename="source.pdf"',
                                 'X-Content-Type-Options': 'nosniff'})

    @app.delete('/api/documents/{document_id}', dependencies=[Depends(authorize)], status_code=204)
    def delete(document_id: UUID):
        if not settings.deletes_enabled:
            raise HTTPException(403, 'Document deletion is disabled for this demo.')
        if not mutations.acquire(blocking=False):
            raise HTTPException(409, 'Another document is being processed. Please try again shortly.')
        try:
            document = repository.get_document(str(document_id))
            if document:
                document.status = 'deleting'
                repository.save_document(document)
                repository.delete(str(document_id))
            return Response(status_code=204)
        finally:
            mutations.release()

    return app


app = create_app()
