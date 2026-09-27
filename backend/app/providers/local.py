"""Offline demonstration only: hashed word vectors and verbatim excerpts, not AI."""
import hashlib
import math
import re
from app.models import Claim, ModelAnswer

STOP_WORDS = set('a an the is are was were what which who how does do did to of in on for and or with from it as tell me about'.split())


def terms(text: str) -> set[str]:
    return set(re.findall(r'[a-z0-9]+', text.lower())) - STOP_WORDS


class LocalEmbeddings:
    def embed(self, texts):
        vectors = []
        for text in texts:
            vector = [0.0] * 256
            for word in terms(text):
                index = int(hashlib.sha256(word.encode()).hexdigest()[:8], 16) % 256
                vector[index] += 1
            norm = math.sqrt(sum(value * value for value in vector)) or 1
            vectors.append([value / norm for value in vector])
        return vectors, 0.0


class LocalAnswers:
    def answer(self, question, chunks):
        question_terms = terms(question)
        ranked = []
        for chunk in chunks:
            overlap = len(question_terms & terms(chunk.text))
            if overlap >= max(2, math.ceil(len(question_terms) * 0.5)):
                ranked.append((overlap, chunk))
        ranked.sort(key=lambda item: item[0], reverse=True)
        claims = [Claim(text=chunk.text, source_ids=[chunk.id]) for _, chunk in ranked[:2]]
        return ModelAnswer(insufficient_evidence=not claims, claims=claims), 0.0
