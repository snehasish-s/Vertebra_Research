from typing import Protocol
from app.models import Chunk, ModelAnswer


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> tuple[list[list[float]], float]:
        """Return vectors and estimated USD cost."""
        ...


class AnswerProvider(Protocol):
    def answer(self, question: str, chunks: list[Chunk]) -> tuple[ModelAnswer, float]:
        ...
