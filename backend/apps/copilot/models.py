"""
Module 9 — Compliance Copilot (Vertex AI RAG, me-central2).

Knowledge base (LCGPA/ZATCA rulebooks) vectorized with Vertex Text Embeddings and
stored natively via pgvector. Django is the zero-trust middleman: it verifies the
RBAC token and physically restricts the similarity search to authorized document
categories before calling Gemini. Global rulebooks have tenant=null; tenant docs
are RLS-scoped.
"""
from django.db import models
from pgvector.django import HnswIndex, VectorField

from apps.common.models import BaseModel

EMBEDDING_DIM = 768  # Vertex text-embedding-004


class DocCategory(models.TextChoices):
    LCGPA = "LCGPA", "LCGPA"
    ZATCA = "ZATCA", "ZATCA"
    HR = "HR", "HR"
    FINANCE = "FINANCE", "Finance"
    PROCUREMENT = "PROCUREMENT", "Procurement"


class KnowledgeDocument(BaseModel):
    tenant = models.ForeignKey(
        "tenancy.Tenant", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=DocCategory.choices)
    is_global = models.BooleanField(default=False)
    source = models.CharField(max_length=512, blank=True)


class DocumentChunk(BaseModel):
    tenant = models.ForeignKey(
        "tenancy.Tenant", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    document = models.ForeignKey(
        KnowledgeDocument, on_delete=models.CASCADE, related_name="chunks"
    )
    content = models.TextField()
    embedding = VectorField(dimensions=EMBEDDING_DIM)
    category = models.CharField(max_length=20, choices=DocCategory.choices)

    class Meta:
        indexes = [
            HnswIndex(
                name="docchunk_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]


class CopilotConversation(BaseModel):
    tenant = models.ForeignKey(
        "tenancy.Tenant", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="+")


class CopilotMessage(BaseModel):
    conversation = models.ForeignKey(
        CopilotConversation, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=12)  # user | assistant
    content = models.TextField()
    retrieved_chunk_ids = models.JSONField(default=list)
