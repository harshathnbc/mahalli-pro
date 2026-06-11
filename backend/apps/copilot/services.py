"""
Compliance Copilot — Vertex AI RAG with zero-trust RBAC routing (Module 9).

Django is the strict middleman: it verifies the user's role and physically restricts
the pgvector similarity search to the document categories that role may see (e.g.
HR is locked out of FINANCE docs) BEFORE building the Gemini prompt. The React
frontend never talks to Vertex directly.

Vertex calls are lazily imported; the RBAC gating + chunking are pure & testable.
"""
from __future__ import annotations

from apps.accounts.models import Role
from apps.copilot.models import (
    CopilotConversation,
    CopilotMessage,
    DocCategory,
    DocumentChunk,
    KnowledgeDocument,
)

# Which knowledge categories each role may query. Global rulebooks (LCGPA/ZATCA)
# are visible to everyone; department docs are siloed.
_BASE = {DocCategory.LCGPA, DocCategory.ZATCA}
ROLE_CATEGORIES: dict[str, set[str]] = {
    Role.MASTER_ADMIN: set(DocCategory.values),
    Role.SUPER_ADMIN: set(DocCategory.values),
    Role.COMPANY_ADMIN: set(DocCategory.values),
    Role.HR_ADMIN: _BASE | {DocCategory.HR},
    Role.PROCUREMENT_ADMIN: _BASE | {DocCategory.PROCUREMENT},
    Role.FINANCE_ADMIN: _BASE | {DocCategory.FINANCE},
}


def allowed_categories(role: str) -> set[str]:
    """Zero-trust: the doc categories a role is permitted to retrieve from."""
    return ROLE_CATEGORIES.get(role, set(_BASE))


def chunk_text(text: str, *, size: int = 1000, overlap: int = 150) -> list[str]:
    """Pure fixed-size sliding-window chunker (character-based)."""
    if size <= 0:
        raise ValueError("size must be positive")
    text = text.strip()
    if not text:
        return []
    step = max(1, size - overlap)
    return [text[i : i + size] for i in range(0, len(text), step) if text[i : i + size].strip()]


# --- Vertex-backed operations (lazy; require GCP config) ----------------------
def embed(texts: list[str]) -> list[list[float]]:
    from apps.common.gcp import embedding_model

    model = embedding_model()
    return [e.values for e in model.get_embeddings(texts)]


def ingest_document(*, title: str, category: str, text: str, tenant=None, is_global=False) -> KnowledgeDocument:
    """Chunk → embed → store as pgvector rows for later retrieval."""
    doc = KnowledgeDocument.objects.create(
        title=title, category=category, is_global=is_global, tenant=tenant
    )
    chunks = chunk_text(text)
    vectors = embed(chunks)
    DocumentChunk.objects.bulk_create(
        [
            DocumentChunk(
                document=doc, tenant=tenant, category=category,
                content=chunk, embedding=vec,
            )
            for chunk, vec in zip(chunks, vectors)
        ]
    )
    return doc


def retrieve(query: str, *, role: str, tenant_id, top_k: int = 5) -> list[DocumentChunk]:
    """
    pgvector cosine similarity search, physically restricted to the role's allowed
    categories and to global docs OR this tenant's docs.
    """
    from pgvector.django import CosineDistance

    categories = allowed_categories(role)
    query_vec = embed([query])[0]
    return list(
        DocumentChunk.objects.filter(category__in=categories)
        .filter(tenant_id__in=[None, tenant_id])
        .order_by(CosineDistance("embedding", query_vec))[:top_k]
    )


def answer(*, conversation: CopilotConversation, query: str, role: str) -> CopilotMessage:
    """Retrieve authorized context, prompt Gemini for a grounded answer, persist turn."""
    from apps.common.gcp import generative_model

    chunks = retrieve(query, role=role, tenant_id=conversation.tenant_id)
    context = "\n\n".join(c.content for c in chunks)
    prompt = (
        "You are a Saudi LCGPA compliance assistant. Answer ONLY from the context "
        "below; if it is insufficient, say so. Do not invent figures.\n\n"
        f"Context:\n{context}\n\nQuestion: {query}"
    )
    CopilotMessage.objects.create(conversation=conversation, role="user", content=query)
    response = generative_model().generate_content(prompt)
    return CopilotMessage.objects.create(
        conversation=conversation,
        role="assistant",
        content=response.text,
        retrieved_chunk_ids=[str(c.id) for c in chunks],
    )
