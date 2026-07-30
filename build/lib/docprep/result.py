from __future__ import annotations

import dataclasses
from pathlib import Path


@dataclasses.dataclass
class ConversionResult:
    source_path: Path
    markdown: str
    format_detected: str
    pipeline_used: str
    page_count: int | None
    escalated: bool
    processing_time_seconds: float
    warnings: list[str] = dataclasses.field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source_path": str(self.source_path),
            "markdown": self.markdown,
            "format_detected": self.format_detected,
            "pipeline_used": self.pipeline_used,
            "page_count": self.page_count,
            "escalated": self.escalated,
            "processing_time_seconds": self.processing_time_seconds,
            "warnings": self.warnings,
        }
