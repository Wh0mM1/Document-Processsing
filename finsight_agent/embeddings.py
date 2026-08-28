import hashlib
import json
import math
import os
import re
import urllib.request
from collections import Counter


class HashEmbeddingProvider:
    name = "hash-embedding-v1"
    def __init__(self, dimensions=384): self.dimensions = dimensions

    def embed(self, texts):
        result = []
        for text in texts:
            vector = [0.0]*self.dimensions
            for token, count in Counter(re.findall(r"[a-z0-9]+", text.lower())).items():
                vector[int(hashlib.sha256(token.encode()).hexdigest(), 16) %
                       self.dimensions] += count
            norm = math.sqrt(sum(v*v for v in vector)) or 1.0
            result.append([v/norm for v in vector])
        return result


class SentenceTransformerEmbeddingProvider:
    name = "sentence-transformers"

    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name, local_files_only=True)
        self.dimensions = self.model.get_sentence_embedding_dimension()

    def embed(self, texts): return self.model.encode(
        texts, normalize_embeddings=True).tolist()


class OllamaEmbeddingProvider:
    name = "ollama"

    def __init__(self, model_name="nomic-embed-text", base_url="http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url.rstrip('/').removesuffix('/v1')
        self.dimensions = 768

    def embed(self, texts):
        request = urllib.request.Request(self.base_url+'/api/embed', data=json.dumps(
            {'model': self.model_name, 'input': texts}).encode(), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read())['embeddings']


def configured_embeddings():
    provider = os.getenv("FINSIGHT_EMBEDDINGS", "hash")
    if provider == "sentence_transformers":
        return SentenceTransformerEmbeddingProvider(os.getenv("FINSIGHT_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
    if provider == "ollama":
        return OllamaEmbeddingProvider(os.getenv("FINSIGHT_EMBEDDING_MODEL", "nomic-embed-text"), os.getenv("FINSIGHT_EMBEDDING_BASE_URL", "http://localhost:11434"))
    return HashEmbeddingProvider()
