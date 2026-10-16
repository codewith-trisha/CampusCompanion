"""
core/rag_engine.py
-------------------
This is the "brain" of the assistant. It has three jobs:

1. embed_text()         -> turn any text into a vector (a list of numbers)
                           using a free, local model (no API key, no cost).
2. search_documents()   -> given a student's question, find the most relevant
                           CollegeInformation rows using vector similarity.
3. ask_gemini()         -> send the assembled context + question to Google
                           Gemini and get back a natural-language answer.

Keeping all of this in one file makes the rest of the app (views.py) simple:
views.py just calls these three functions and doesn't need to know HOW
embeddings or the LLM work.
"""

import os
import threading

from django.conf import settings

# --------------------------------------------------------------------------
# 1. EMBEDDING MODEL
# Loaded once per process (it's ~90MB) and re-used for every request, since
# loading it fresh every time would be slow. _lock keeps this thread-safe.
# --------------------------------------------------------------------------
_model = None
_model_lock = threading.Lock()


def _get_embedding_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer
                # all-MiniLM-L6-v2: small (~90MB), fast, good enough accuracy
                # for FAQ-style matching. Downloads once from Hugging Face,
                # then is cached locally.
                _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed_text(text: str) -> list:
    """Convert a string into a 384-dimensional vector."""
    model = _get_embedding_model()
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()


# --------------------------------------------------------------------------
# 2. VECTOR STORE (ChromaDB) — persisted to disk at settings.VECTOR_DB_DIR
# --------------------------------------------------------------------------
_chroma_client = None


def _get_collection():
    global _chroma_client
    if _chroma_client is None:
        import chromadb
        os.makedirs(settings.VECTOR_DB_DIR, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(settings.VECTOR_DB_DIR))
    return _chroma_client.get_or_create_collection(name="college_information")


def index_document(doc_id: int, title: str, content: str, category: str):
    """
    Embed one CollegeInformation row and store/update it in Chroma.
    Called by the `build_vector_index` management command whenever data changes.
    """
    collection = _get_collection()
    vector = embed_text(f"{title}. {content}")
    collection.upsert(
        ids=[str(doc_id)],
        embeddings=[vector],
        documents=[content],
        metadatas=[{"title": title, "category": category}],
    )


def search_documents(question: str, top_k: int = 5) -> list[dict]:
    """
    Find the top_k CollegeInformation entries most semantically similar
    to the student's question. Returns [] if the index is empty/missing.
    """
    collection = _get_collection()
    if collection.count() == 0:
        return []

    query_vector = embed_text(question)
    results = collection.query(query_embeddings=[query_vector], n_results=min(top_k, collection.count()))

    matches = []
    for doc, meta, distance in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        matches.append({"title": meta["title"], "category": meta["category"], "content": doc, "distance": distance})
    return matches


# --------------------------------------------------------------------------
# 3. LLM CALL (Google Gemini — free tier, get a key at aistudio.google.com)
# --------------------------------------------------------------------------
_genai_client = None


def _get_genai_client():
    global _genai_client
    if _genai_client is None:
        from google import genai
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to your .env file — "
                "get a free key at https://aistudio.google.com"
            )
        _genai_client = genai.Client(api_key=api_key)
    return _genai_client


def ask_gemini(system_prompt: str, user_message: str, history: list[dict] | None = None,
                model: str = "gemini-flash-latest") -> str:
    """
    Send the assembled context + question to Gemini and return plain text.

    `history` is an optional list of prior turns in this conversation, each shaped
    like {"role": "user"|"model", "text": "..."}. Passing it in lets Gemini answer
    follow-up questions like "what about hostel timings?" that only make sense in
    light of what was already discussed.
    """
    client = _get_genai_client()

    contents = []
    for turn in (history or []):
        contents.append({"role": turn["role"], "parts": [{"text": turn["text"]}]})
    contents.append({"role": "user", "parts": [{"text": user_message}]})

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config={
            "system_instruction": system_prompt,
            "temperature": 0.3,
        },
    )
    return response.text