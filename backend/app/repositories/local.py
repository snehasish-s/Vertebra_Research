"""Small, durable local adapter. Never use this on Render's temporary filesystem."""
from contextlib import contextmanager
import sqlite3
from app.models import Chunk, Document


class LocalRepository:
    def __init__(self, directory):
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / 'research.sqlite3'
        with self.connect() as connection:
            connection.execute('CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, data TEXT NOT NULL, pdf BLOB)')
            connection.execute('CREATE TABLE IF NOT EXISTS chunks (id TEXT PRIMARY KEY, document_id TEXT NOT NULL, data TEXT NOT NULL)')

    @contextmanager
    def connect(self):
        # SQLite's own context manager commits but does not close the handle.
        # Explicit close also lets Windows release/delete temporary test databases.
        connection = sqlite3.connect(self.path, timeout=15)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def list_documents(self):
        with self.connect() as connection:
            rows = connection.execute('SELECT data FROM documents ORDER BY rowid DESC').fetchall()
        return [Document.model_validate_json(row[0]) for row in rows]

    def get_document(self, document_id):
        with self.connect() as connection:
            row = connection.execute('SELECT data FROM documents WHERE id=?', (document_id,)).fetchone()
        return Document.model_validate_json(row[0]) if row else None

    def save_document(self, document):
        with self.connect() as connection:
            connection.execute('INSERT INTO documents(id,data) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',
                               (document.id, document.model_dump_json()))

    def save_pdf(self, document_id, content):
        with self.connect() as connection:
            connection.execute('UPDATE documents SET pdf=? WHERE id=?', (content, document_id))

    def read_pdf(self, document_id):
        with self.connect() as connection:
            row = connection.execute('SELECT pdf FROM documents WHERE id=?', (document_id,)).fetchone()
        if not row or row[0] is None:
            raise FileNotFoundError('PDF is unavailable.')
        return row[0]

    def save_chunks(self, chunks):
        with self.connect() as connection:
            connection.executemany('INSERT INTO chunks VALUES(?,?,?)',
                                   [(item.id, item.document_id, item.model_dump_json()) for item in chunks])

    def search(self, vector, limit, threshold):
        ready_ids = {item.id for item in self.list_documents() if item.status == 'ready'}
        with self.connect() as connection:
            rows = connection.execute('SELECT data FROM chunks').fetchall()
        matches = []
        for row in rows:
            item = Chunk.model_validate_json(row[0])
            if item.document_id in ready_ids:
                item.score = sum(a * b for a, b in zip(vector, item.embedding))
                if item.score >= threshold:
                    matches.append(item)
        return sorted(matches, key=lambda item: item.score, reverse=True)[:limit]

    def delete(self, document_id):
        with self.connect() as connection:
            connection.execute('DELETE FROM chunks WHERE document_id=?', (document_id,))
            connection.execute('DELETE FROM documents WHERE id=?', (document_id,))
