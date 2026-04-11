"""
sentinel.scanner.knowledge
~~~~~~~~~~~~~~~~~~~~~~~~~~
Static knowledge base: Python package → parent company → jurisdiction.

This table is conservative. "Unknown" is better than guessing.
When in doubt, err toward "Unknown" — the scanner must not invent
jurisdictions it cannot verify.

Each entry also records whether the package is *typically* in a
Sentinel critical path. The scanner marks packages as critical-path
when they appear in the installed environment *and* this flag is set.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PackageKnowledge:
    parent_company: str
    jurisdiction: str  # "US", "EU", "UK", "Neutral", "Unknown"
    cloud_act_exposure: bool
    typically_critical_path: bool
    notes: str = ""


# Key = normalised package name (lowercase, dashes preserved).
PACKAGE_KNOWLEDGE: dict[str, PackageKnowledge] = {
    # --- US cloud providers (CLOUD Act) ---------------------------------
    "boto3":                 PackageKnowledge("Amazon",   "US", True,  True,  "AWS SDK"),
    "botocore":              PackageKnowledge("Amazon",   "US", True,  True,  "AWS SDK core"),
    "aws-sdk":               PackageKnowledge("Amazon",   "US", True,  True,  "AWS SDK"),
    "aiobotocore":           PackageKnowledge("Amazon",   "US", True,  True,  "Async AWS SDK"),
    "azure-core":            PackageKnowledge("Microsoft","US", True,  True,  "Azure SDK core"),
    "azure-identity":        PackageKnowledge("Microsoft","US", True,  True,  "Azure auth"),
    "azure-storage-blob":    PackageKnowledge("Microsoft","US", True,  True,  "Azure blob storage"),
    "azure-ai-ml":           PackageKnowledge("Microsoft","US", True,  True,  "Azure ML"),
    "google-cloud-storage":  PackageKnowledge("Alphabet", "US", True,  True,  "GCS"),
    "google-cloud-aiplatform":PackageKnowledge("Alphabet","US", True,  True,  "Vertex AI"),
    "google-api-python-client":PackageKnowledge("Alphabet","US",True, True,  "Google APIs"),
    "google-auth":           PackageKnowledge("Alphabet", "US", True,  True,  "Google auth"),
    "firebase-admin":        PackageKnowledge("Alphabet", "US", True,  True,  "Firebase"),

    # --- US LLM providers (CLOUD Act) -----------------------------------
    "openai":                PackageKnowledge("OpenAI",       "US", True, True, "OpenAI client"),
    "anthropic":             PackageKnowledge("Anthropic PBC","US", True, True, "Anthropic client"),
    "cohere":                PackageKnowledge("Cohere",       "CA", False,True, "Canadian, not CLOUD Act"),
    "replicate":             PackageKnowledge("Replicate",    "US", True, True, "Model hosting"),
    "together":              PackageKnowledge("Together AI",  "US", True, True, "Model hosting"),

    # --- US observability / LLMOps (CLOUD Act) --------------------------
    "langsmith":             PackageKnowledge("LangChain Inc.","US", True,  True,  "Hosted LangSmith"),
    "langchain":             PackageKnowledge("LangChain Inc.","US", True,  False, "Framework; lib itself neutral"),
    "langchain-core":        PackageKnowledge("LangChain Inc.","US", True,  False, "Core abstractions"),
    "langchain-openai":      PackageKnowledge("LangChain Inc.","US", True,  False, "OpenAI integration"),
    "langchain-anthropic":   PackageKnowledge("LangChain Inc.","US", True,  False, "Anthropic integration"),
    "langgraph":             PackageKnowledge("LangChain Inc.","US", True,  False, "State-machine agents"),
    "helicone":              PackageKnowledge("Helicone Inc.","US",  True,  True,  "Proxy observability"),
    "wandb":                 PackageKnowledge("Weights & Biases","US",True, True,  "W&B client"),
    "mlflow":                PackageKnowledge("Databricks",   "US", True,  True,  "MLflow client"),
    "datadog":               PackageKnowledge("Datadog",      "US", True,  True,  "Datadog client"),
    "ddtrace":               PackageKnowledge("Datadog",      "US", True,  True,  "Datadog tracer"),
    "sentry-sdk":            PackageKnowledge("Functional Software","US",True,True,"Sentry.io client"),
    "newrelic":              PackageKnowledge("New Relic",    "US", True,  True,  "APM client"),
    "honeycomb-beeline":     PackageKnowledge("Honeycomb",    "US", True,  True,  "Honeycomb client"),

    # --- EU-sovereign (Berlin) ------------------------------------------
    "langfuse":              PackageKnowledge("Langfuse GmbH","EU", False, False, "Berlin, self-hostable"),

    # --- Jurisdiction-neutral open source --------------------------------
    "psycopg2":              PackageKnowledge("PostgreSQL Global Dev Group","Neutral",False,True, "OSS"),
    "psycopg2-binary":       PackageKnowledge("PostgreSQL Global Dev Group","Neutral",False,True, "OSS"),
    "psycopg":               PackageKnowledge("PostgreSQL Global Dev Group","Neutral",False,True, "OSS"),
    "asyncpg":               PackageKnowledge("MagicStack",                 "Neutral",False,True, "OSS"),
    "sqlalchemy":            PackageKnowledge("SQLAlchemy",                 "Neutral",False,False,"OSS"),
    "sqlite3":               PackageKnowledge("SQLite Consortium",          "Neutral",False,True, "Public domain"),
    "redis":                 PackageKnowledge("Redis Ltd.",                 "US",     True, False,"Client; server can be self-hosted"),

    # --- Standards orgs / CNCF -------------------------------------------
    "opentelemetry-api":     PackageKnowledge("CNCF","Neutral",False,False,"Vendor-neutral standard"),
    "opentelemetry-sdk":     PackageKnowledge("CNCF","Neutral",False,False,"Vendor-neutral standard"),
    "opentelemetry-exporter-otlp": PackageKnowledge("CNCF","Neutral",False,False,"OTLP exporter"),
    "opentelemetry-exporter-otlp-proto-grpc": PackageKnowledge("CNCF","Neutral",False,False,"OTLP gRPC"),

    # --- Popular ML/data stack (neutral OSS) -----------------------------
    "numpy":                 PackageKnowledge("NumFOCUS","Neutral",False,False,"OSS"),
    "pandas":                PackageKnowledge("NumFOCUS","Neutral",False,False,"OSS"),
    "scipy":                 PackageKnowledge("NumFOCUS","Neutral",False,False,"OSS"),
    "scikit-learn":          PackageKnowledge("NumFOCUS","Neutral",False,False,"OSS"),
    "torch":                 PackageKnowledge("Linux Foundation","Neutral",False,False,"PyTorch (LF)"),
    "pytorch":               PackageKnowledge("Linux Foundation","Neutral",False,False,"PyTorch (LF)"),
    "transformers":          PackageKnowledge("Hugging Face","EU/US-dual",False,False,"HF library OSS"),
    "datasets":              PackageKnowledge("Hugging Face","EU/US-dual",False,False,"HF library OSS"),
    "huggingface-hub":       PackageKnowledge("Hugging Face","EU/US-dual",True, True, "Hub is US-hosted"),
    "sentence-transformers": PackageKnowledge("UKP Lab","EU",False,False,"TU Darmstadt"),
    "spacy":                 PackageKnowledge("Explosion AI","EU",False,False,"Berlin"),

    # --- Web / stdlib adjacent (neutral) ---------------------------------
    "httpx":                 PackageKnowledge("Encode","Neutral",False,False,"OSS"),
    "requests":              PackageKnowledge("Python Software Foundation","Neutral",False,False,"OSS"),
    "urllib3":               PackageKnowledge("urllib3","Neutral",False,False,"OSS"),
    "aiohttp":               PackageKnowledge("aio-libs","Neutral",False,False,"OSS"),
    "fastapi":               PackageKnowledge("FastAPI","Neutral",False,False,"OSS"),
    "uvicorn":               PackageKnowledge("Encode","Neutral",False,False,"OSS"),
    "starlette":             PackageKnowledge("Encode","Neutral",False,False,"OSS"),
    "pydantic":              PackageKnowledge("Pydantic Services","UK",False,False,"UK company"),
    "pyyaml":                PackageKnowledge("YAML","Neutral",False,False,"OSS"),
    "click":                 PackageKnowledge("Pallets","Neutral",False,False,"OSS"),
    "typer":                 PackageKnowledge("FastAPI","Neutral",False,False,"OSS"),

    # --- Test / dev tooling (not critical path) --------------------------
    "pytest":                PackageKnowledge("pytest-dev","Neutral",False,False,"OSS"),
    "pytest-asyncio":        PackageKnowledge("pytest-dev","Neutral",False,False,"OSS"),
    "pytest-cov":            PackageKnowledge("pytest-cov","Neutral",False,False,"OSS"),
    "coverage":              PackageKnowledge("Coverage.py","Neutral",False,False,"OSS"),
    "ruff":                  PackageKnowledge("Astral","US",False,False,"Dev tooling only"),
    "mypy":                  PackageKnowledge("Python Software Foundation","Neutral",False,False,"OSS"),
    "black":                 PackageKnowledge("Python Software Foundation","Neutral",False,False,"OSS"),
    "hatch":                 PackageKnowledge("Ofek Lev","Neutral",False,False,"OSS"),
    "hatchling":             PackageKnowledge("Ofek Lev","Neutral",False,False,"OSS"),

    # --- AI agent frameworks (many US) ----------------------------------
    "crewai":                PackageKnowledge("CrewAI Inc.",     "US", True,  False, "Agent framework"),
    "autogen":               PackageKnowledge("Microsoft",       "US", True,  False, "Agent framework"),
    "pyautogen":             PackageKnowledge("Microsoft",       "US", True,  False, "Agent framework"),
    "semantic-kernel":       PackageKnowledge("Microsoft",       "US", True,  False, "Agent framework"),
    "llama-index":           PackageKnowledge("LlamaIndex Inc.", "US", True,  False, "RAG framework"),
    "llama-cpp-python":      PackageKnowledge("LlamaIndex Inc.", "US", False, False, "Local inference"),
    "dspy":                  PackageKnowledge("Stanford NLP",    "US", False, False, "Academic"),
    "griptape":              PackageKnowledge("Griptape AI",     "US", True,  False, "Agent framework"),
    "haystack-ai":           PackageKnowledge("deepset GmbH",    "EU", False, False, "Berlin — EU-sovereign"),
    "farm-haystack":         PackageKnowledge("deepset GmbH",    "EU", False, False, "Berlin — legacy Haystack 1.x"),

    # --- Additional US LLM providers (CLOUD Act) ------------------------
    "groq":                  PackageKnowledge("Groq Inc.",       "US", True,  True,  "Groq client"),
    "perplexity-client":     PackageKnowledge("Perplexity AI",   "US", True,  True,  "Perplexity API"),
    "mistralai":             PackageKnowledge("Mistral AI",      "EU", False, True,  "Paris — EU-sovereign"),

    # --- EU-sovereign cloud / infra providers ---------------------------
    "deepl":                 PackageKnowledge("DeepL SE",        "EU", False, False, "German translation"),
    "aleph-alpha-client":    PackageKnowledge("Aleph Alpha GmbH","EU", False, True,  "German LLM"),
    "scaleway":              PackageKnowledge("Scaleway SAS",    "EU", False, False, "French cloud"),
    "hcloud":                PackageKnowledge("Hetzner Online GmbH","EU",False,False,"Hetzner Cloud — German"),
    "ovh":                   PackageKnowledge("OVH SAS",         "EU", False, False, "French cloud"),

    # --- Web / HTTP (neutral but commonly missed) -----------------------
    "httpcore":              PackageKnowledge("Encode",          "Neutral", False, False, "OSS"),
    "anyio":                 PackageKnowledge("agronholm",       "Neutral", False, False, "OSS"),
    "sniffio":               PackageKnowledge("python-trio",     "Neutral", False, False, "OSS"),
    "h11":                   PackageKnowledge("python-hyper",    "Neutral", False, False, "OSS"),
    "h2":                    PackageKnowledge("python-hyper",    "Neutral", False, False, "OSS"),
    "certifi":               PackageKnowledge("Certifi",         "Neutral", False, False, "CA bundle"),
    "charset-normalizer":    PackageKnowledge("Ousret",          "Neutral", False, False, "OSS"),
    "idna":                  PackageKnowledge("Kim Davies",      "Neutral", False, False, "OSS"),

    # --- Observability servers / collectors (self-hostable) -------------
    "prometheus-client":     PackageKnowledge("Prometheus",      "Neutral", False, False, "CNCF client"),
    "grafana-api":           PackageKnowledge("Grafana Labs",    "US",      True,  False, "HQ in US despite OSS core"),

    # --- Vector DBs ------------------------------------------------------
    "pinecone-client":       PackageKnowledge("Pinecone",        "US", True,  True,  "Hosted vector DB"),
    "weaviate-client":       PackageKnowledge("Weaviate B.V.",   "EU", False, True,  "Amsterdam"),
    "qdrant-client":         PackageKnowledge("Qdrant",          "EU", False, True,  "Berlin"),
    "chromadb":              PackageKnowledge("Chroma",          "US", True,  True,  "Hosted or self-hosted"),
    "milvus":                PackageKnowledge("Zilliz",          "US", True,  True,  "Milvus host"),

    # --- Document / PDF processing --------------------------------------
    "pypdf":                 PackageKnowledge("py-pdf",          "Neutral", False, False, "OSS"),
    "pdfplumber":            PackageKnowledge("pdfplumber",      "Neutral", False, False, "OSS"),

    # --- Async / concurrency --------------------------------------------
    "trio":                  PackageKnowledge("python-trio",     "Neutral", False, False, "OSS"),
    "curio":                 PackageKnowledge("Dave Beazley",    "Neutral", False, False, "OSS"),

    # --- Sentinel itself --------------------------------------------------
    "sentinel-kernel":       PackageKnowledge("sentinel-kernel","EU",False,True,"This project"),
}


# ---------------------------------------------------------------------------
# EU-sovereign alternatives map
# ---------------------------------------------------------------------------

#: For each US-owned package, a suggested EU-sovereign alternative.
#: Used by ``sentinel scan --suggest-alternatives``.
EU_ALTERNATIVES: dict[str, str] = {
    "openai":              "mistralai (Mistral AI, Paris) or aleph-alpha-client (Aleph Alpha, Heidelberg)",
    "anthropic":           "mistralai or aleph-alpha-client",
    "cohere":              "mistralai",
    "groq":                "mistralai (no EU hosted inference provider at this latency yet)",
    "google-cloud-storage":"hcloud (Hetzner) or scaleway",
    "boto3":               "hcloud (Hetzner) or scaleway or ovh",
    "azure-storage-blob":  "hcloud (Hetzner) or scaleway",
    "pinecone-client":     "qdrant-client (Berlin) or weaviate-client (Amsterdam)",
    "chromadb":            "qdrant-client or weaviate-client",
    "milvus":              "qdrant-client or weaviate-client",
    "wandb":               "mlflow self-hosted, or langfuse (Berlin)",
    "mlflow":              "langfuse (Berlin, self-hostable)",
    "datadog":             "prometheus-client + grafana (self-hosted)",
    "sentry-sdk":          "glitchtip (self-hosted, Sentry-compatible)",
    "langchain":           "haystack-ai (deepset, Berlin)",
    "llama-index":         "haystack-ai",
    "crewai":              "haystack-ai",
    "autogen":             "haystack-ai",
    "semantic-kernel":     "haystack-ai",
    "helicone":            "langfuse",
    "langsmith":           "langfuse",
}


def suggest_alternative(package_name: str) -> str | None:
    """Return an EU-sovereign alternative for the given US package, if known."""
    return EU_ALTERNATIVES.get(_normalise(package_name))


def lookup(package_name: str) -> PackageKnowledge | None:
    """Return knowledge for a package or None if unknown."""
    return PACKAGE_KNOWLEDGE.get(_normalise(package_name))


def _normalise(name: str) -> str:
    return name.strip().lower().replace("_", "-")
