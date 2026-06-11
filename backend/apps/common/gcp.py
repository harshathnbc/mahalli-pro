"""
Google Cloud client factories (Vertex AI + Document AI), pinned to me-central2.

All google-cloud imports are lazy (done inside functions) so the rest of the app —
and `manage.py check` / migrations — work without the heavy GCP SDKs installed in
every environment. Production (Phase 1, GCP Dammam) installs them via requirements.txt.
"""
from __future__ import annotations

from django.conf import settings


class GCPNotConfigured(RuntimeError):
    """Raised when a GCP-backed feature is used without the required configuration."""


def _cfg(key: str) -> str:
    value = settings.GCP.get(key, "")
    if not value:
        raise GCPNotConfigured(f"settings.GCP['{key}'] is not configured.")
    return value


def documentai_client():
    from google.cloud import documentai  # lazy

    location = settings.GCP.get("LOCATION", "me-central2")
    opts = {"api_endpoint": f"{location}-documentai.googleapis.com"}
    return documentai.DocumentProcessorServiceClient(client_options=opts)


def processor_name() -> str:
    project = _cfg("PROJECT_ID")
    location = settings.GCP.get("LOCATION", "me-central2")
    processor = _cfg("DOCAI_PROCESSOR_ID")
    return f"projects/{project}/locations/{location}/processors/{processor}"


def init_vertex() -> None:
    import vertexai  # lazy

    vertexai.init(project=_cfg("PROJECT_ID"), location=settings.GCP.get("LOCATION", "me-central2"))


def embedding_model():
    from vertexai.language_models import TextEmbeddingModel  # lazy

    init_vertex()
    return TextEmbeddingModel.from_pretrained(settings.GCP.get("EMBEDDING_MODEL", "text-embedding-004"))


def generative_model():
    from vertexai.generative_models import GenerativeModel  # lazy

    init_vertex()
    return GenerativeModel(settings.GCP.get("GENERATIVE_MODEL", "gemini-1.5-flash"))
