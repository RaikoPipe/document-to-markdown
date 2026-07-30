"""docprep — Document preprocessing pipeline for LLM/RAG ingestion."""

from docprep.entrypoint import convert
from docprep.result import ConversionResult

__all__ = ["convert", "ConversionResult"]
