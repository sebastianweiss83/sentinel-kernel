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

    # --- Sentinel itself --------------------------------------------------
    "sentinel-kernel":       PackageKnowledge("sentinel-kernel","EU",False,True,"This project"),
}


def lookup(package_name: str) -> PackageKnowledge | None:
    """Return knowledge for a package or None if unknown."""
    return PACKAGE_KNOWLEDGE.get(_normalise(package_name))


def _normalise(name: str) -> str:
    return name.strip().lower().replace("_", "-")
