# docprep

Document preprocessing pipeline — converts any common document format to Markdown for LLM/RAG ingestion.

## Quick start

```bash
# Install with the provider(s) you need
pip install -e ".[ollama]"          # or: mistral, openai, gemini, anthropic, all

# Create a .env with your API key (auto-loaded by the CLI)
echo "OLLAMA_API_KEY=sk-..." > .env

# Create a config
cp docprep.example.yaml docprep.yaml  # then edit

# Convert a document
docprep convert document.pdf --config docprep.yaml -v
```

## Pipeline routing

```
                         Input file
                              |
                              v
                    classify() — MIME detection
                    + PDF probing (text vs scanned)
                              |
            +-----------------+-----------------+------------------+
            |                 |                 |                  |
     Office MIME         application/pdf     Image MIME        Other
  (DOCX, XLSX, PPTX,       |             (PNG, JPEG,            |
   HTML, CSV, TXT,    +-----+-----+        TIFF, etc.)          |
   MD, XML, EPUB)     |           |              |              |
        |        Native text   Scanned           |              |
        |        (>20 chars   (<50% of           |              |
        |         per page)   sampled pages       |              |
        |             |       have text)          |              |
        v             v           v              v              v
   Path B          Path A      Path C          Path C     UnsupportedFormatError
  Standard        Standard      VLM             VLM
  pipeline        pipeline    pipeline        pipeline
  (Docling +      (Docling +  (Docling VLM    (Docling VLM
   EasyOCR)        EasyOCR)    preset)         preset)
        |             |           |              |
        |             |           |              |
        v             v           v              v
  +-----+-------------+-----------+--------------+-----+
  |  Picture processing (two-stage VLM) if describe_images=true |
  |                                                             |
  |  Stage 1: Judge — VLM classifies image as                   |
  |           "text_only" or "needs_interpretation"             |
  |                                                             |
  |  Stage 2: OCR (text_only) or Interpret (needs_interpretation|
  |           / ambiguous) — VLM produces text/markdown         |
  |                                                             |
  |  Result text replaces base64 image in markdown              |
  +-------------------------+-----------------------------------+
                            |
                            v
                   Quality gate (should_escalate)
                            |
          +-----------------+------------------+------------------+
          |                 |                  |                  |
     Empty output    PDF + low text      Garbled output      Otherwise
                     density             (>20% non-                |
                     (<50 chars/page)    printable)                |
          |                 |                  |                  |
          +-----------------+------------------+                  |
                            |                                     |
                            v                                     |
                   If fallback configured:                        |
                   Path D: VLM API fallback                       |
                   (Mistral | OpenAI | Gemini |                   |
                    Anthropic | Ollama)                           |
                   Renders pages as images                        |
                   -> sends to VLM -> markdown                    |
                            |                                     |
                            +-------------------------------------+
                            |
                            v
                      ConversionResult
                      (markdown, pipeline_used,
                       escalated, warnings, ...)
```

### Path summary

| Path | Trigger | Handler | Description |
|------|---------|---------|-------------|
| **A** | Native PDF (has selectable text) | `convert_standard` | Docling standard pipeline + EasyOCR + picture description |
| **B** | Office format (DOCX, XLSX, PPTX, HTML, etc.) | `convert_standard` | Docling standard pipeline + EasyOCR + picture description |
| **C** | Scanned PDF or image file | `convert_vlm` | Docling VLM pipeline (uses `vlm_preset`) |
| **D** | Quality gate fails + fallback configured | `convert_with_fallback` | VLM API provider renders pages as images |

### Image handling

When `describe_images: true` and a fallback VLM endpoint is configured, each `PictureItem` found in the document goes through a **two-stage VLM process**:

- **Standard pipeline (Paths A/B):** Docling's enrichment pipe sends each image through a custom `TwoStagePictureModel`:
  1. **Judge call** — the VLM classifies the image as `text_only` (scanned text, text screenshot) or `needs_interpretation` (charts, diagrams, photos, logos)
  2. **OCR or interpret call** — `text_only` images get a fast OCR prompt (extract text only); `needs_interpretation` images get a full interpretation prompt (convert to Markdown, describe charts/figures). Ambiguous judge responses default to interpretation (safe — no information lost)
  
  The result text is stored on `item.meta.description` and emitted in the markdown with a `[Description]` label. Base64 image data is suppressed.
- **VLM pipeline (Path C):** Processes whole page images directly — picture description is not applicable.
- **Fallback (Path D):** Renders pages as images and sends them to the VLM provider for full-page conversion.

When `describe_images: false`, images are emitted as base64 (`embed_images: true`) or `<!-- image -->` placeholders (`embed_images: false`).

## Configuration

### Precedence (highest to lowest)

1. **CLI flags** — `--fallback-provider`, `--vlm-preset`, `--no-fallback`
2. **Environment variables** — `DOCPREP_FALLBACK_PROVIDER`, `DOCPREP_FALLBACK_MODEL`, `DOCPREP_FALLBACK_BASE_URL`
3. **YAML file** — passed via `--config docprep.yaml`
4. **Defaults** — `PipelineConfig` dataclass defaults

### YAML structure

```yaml
pipeline:
  vlm_preset: granite_docling       # Docling VLM preset for Path C
  ocr_languages: [en]               # EasyOCR language codes
  embed_images: true                # embed images as base64 (true) or placeholders (false)
  render_chart_images: true         # render Excel charts as images (requires LibreOffice)
  describe_images: true             # send images to VLM for two-stage processing
  picture_judge_prompt: "Look at this image and classify it as..."  # stage 1
  picture_ocr_prompt: "Extract all text from this image..."         # stage 2 for text_only
  picture_interpret_prompt: "Convert this image to Markdown..."     # stage 2 for needs_interpretation
  picture_description_timeout: 60   # seconds per image API call
  picture_description_concurrency: 1
  picture_area_threshold: 0.01      # min fraction of page area to describe

quality_gate:
  min_text_density: 50              # min chars per page (PDFs only)
  max_garbled_ratio: 0.20           # max fraction of non-printable characters (all formats)

fallback:
  enabled: true                     # toggle quality-gate escalation
  provider: ollama                  # mistral | openai | gemini | anthropic | ollama
  model: glm-ocr                    # VLM model name (bare, no ollama/ prefix)
  base_url: http://localhost:11434/v1  # OpenAI-compatible endpoint
  max_pages: 50                     # max pages to send to VLM API
  timeout_seconds: 30               # timeout per API call
```

### Environment variables

| Variable | Purpose |
|----------|---------|
| `OLLAMA_API_KEY` | API key for Ollama fallback |
| `MISTRAL_API_KEY` | API key for Mistral fallback |
| `OPENAI_API_KEY` | API key for OpenAI fallback |
| `GEMINI_API_KEY` | API key for Gemini fallback |
| `ANTHROPIC_API_KEY` | API key for Anthropic fallback |
| `DOCPREP_FALLBACK_PROVIDER` | Override fallback provider |
| `DOCPREP_FALLBACK_MODEL` | Override fallback model |
| `DOCPREP_FALLBACK_BASE_URL` | Override fallback base URL |

### `.env` file

The CLI auto-loads `.env` from the current working directory at startup. Shell `export` values take precedence over `.env` values (`override=False`). This file should contain your API keys:

```
OLLAMA_API_KEY=sk-...
```

Add `.env` to `.gitignore` (already done in this repo) to avoid committing secrets.

## CLI usage

### `docprep convert`

```
docprep convert SOURCE [OPTIONS]

  Convert a document to Markdown.

Options:
  -o, --output PATH           Write to file instead of stdout
  --format [md|json]          Output format (default: md)
  --fallback-provider [mistral|openai|gemini|anthropic|ollama]
                              Override fallback provider
  --vlm-preset TEXT           Override VLM preset
  --config PATH               Path to YAML config file
  --no-fallback               Disable quality-gate escalation
  -v, --verbose               Verbose logging + pipeline stats
  -q, --quiet                 Suppress warnings
```

### `docprep info`

```
docprep info SOURCE

  Show detected MIME type, page count, and recommended processing path.
```

### Examples

```bash
# Convert to stdout
docprep convert document.pdf --config docprep.yaml -v

# Convert to file with JSON metadata
docprep convert report.docx -o report.md --format json --config docprep.yaml

# Inspect a file without converting
docprep info spreadsheet.xlsx

# Disable fallback escalation
docprep convert scan.pdf --config docprep.yaml --no-fallback
```

### Batch conversion (fish shell)

```fish
mkdir -p output; and \
for f in data/*.xlsx data/*.pptx
    set name (basename "$f" | sed 's/\.[^.]*$//')
    docprep convert "$f" -o "output/$name.md" --config docprep.yaml -v
end
```

### Legacy `.ppt` files

Docling only supports `.pptx`, not legacy `.ppt` (PowerPoint 97-2003). Convert first:

```bash
soffice --headless --convert-to pptx --outdir data/ data/*.ppt
```

## Providers

| Provider | Install extra | API key env var | Notes |
|----------|--------------|-----------------|-------|
| Ollama | `pip install -e ".[ollama]"` | `OLLAMA_API_KEY` | OpenAI-compatible endpoint; use bare model name (no `ollama/` prefix); requires `fallback.model` + `fallback.base_url` |
| Mistral | `pip install -e ".[mistral]"` | `MISTRAL_API_KEY` | Uses Mistral OCR API |
| OpenAI | `pip install -e ".[openai]"` | `OPENAI_API_KEY` | Uses GPT-4o vision |
| Gemini | `pip install -e ".[gemini]"` | `GEMINI_API_KEY` | Uses Gemini 2.0 Flash |
| Anthropic | `pip install -e ".[anthropic]"` | `ANTHROPIC_API_KEY` | Uses Claude Sonnet |

Install all providers: `pip install -e ".[all]"`

### Ollama notes

- **Model name:** Use the bare name (`glm-ocr`, `llama3.2-vision`) without the `ollama/` prefix. The prefix is only for `ollama pull`, not API calls.
- **Base URL:** Point to the `/v1` endpoint, e.g. `http://localhost:11434/v1` or `https://your-host/v1`.
- **Picture description:** The same endpoint serves both image description (per-image during standard conversion) and document fallback (whole-page rendering on quality-gate failure).
- **Local Ollama:** If running locally with no auth, set `OLLAMA_API_KEY` to any placeholder string — the `openai` client requires a value but Ollama ignores it.

## Programmatic usage

```python
from pathlib import Path
from docprep.config import PipelineConfig
from docprep.entrypoint import convert

config = PipelineConfig.from_sources(yaml_path=Path("docprep.yaml"))
result = convert("document.pdf", config)

print(result.markdown)
print(f"Pipeline: {result.pipeline_used}")
print(f"Escalated: {result.escalated}")
print(f"Warnings: {result.warnings}")
```

## Supported formats

| MIME type | Processing path |
|-----------|----------------|
| `application/pdf` (native text) | Path A — Standard pipeline |
| `application/pdf` (scanned) | Path C — VLM pipeline |
| `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | Path B — Standard pipeline |
| `application/vnd.openxmlformats-officedocument.presentationml.presentation` | Path B — Standard pipeline |
| `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | Path B — Standard pipeline |
| `application/msword` | Path B — Standard pipeline |
| `application/vnd.ms-excel` | Path B — Standard pipeline |
| `application/vnd.ms-powerpoint` | Path B — Standard pipeline |
| `application/epub+zip` | Path B — Standard pipeline |
| `text/html` | Path B — Standard pipeline |
| `text/csv` | Path B — Standard pipeline |
| `text/plain` | Path B — Standard pipeline |
| `text/xml` | Path B — Standard pipeline |
| `text/markdown` | Path B — Standard pipeline |
| `image/png` | Path C — VLM pipeline |
| `image/jpeg` | Path C — VLM pipeline |
| `image/tiff` | Path C — VLM pipeline |
| `image/webp` | Path C — VLM pipeline |
| `image/bmp` | Path C — VLM pipeline |
| `image/gif` | Path C — VLM pipeline |

## Quality gate

The quality gate (`should_escalate`) checks conversion output and triggers Path D (VLM fallback) when:

| Check | Applies to | Default threshold |
|-------|-----------|-------------------|
| Empty output | All formats | Any empty/whitespace-only markdown |
| Low text density | **PDFs only** | < 50 chars/page (`min_text_density`) |
| Garbled output | All formats | > 20% non-printable characters (`max_garbled_ratio`) |

The density check is restricted to PDFs because office formats (XLSX, PPTX, DOCX) don't have meaningful "page counts" — pymupdf returns misleading values (e.g. row counts for Excel) that would cause false escalations on every office document.

## Testing

```bash
ruff check src tests
pytest
```

Pytest markers:
- `integration` — requires docling and real document fixtures
- `api` — requires external API keys