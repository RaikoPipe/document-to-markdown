from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

from docprep.config import PipelineConfig
from docprep.entrypoint import convert
from docprep.router import UnsupportedFormatError, classify
from docprep.utils.mime import detect_mime


def _load_env() -> None:
    """Load .env from the current directory and the docprep install root."""
    cwd_env = Path.cwd() / ".env"
    if cwd_env.exists():
        load_dotenv(cwd_env, override=False)
    else:
        load_dotenv(override=False)


@click.group()
def main():
    """docprep — Document preprocessing pipeline."""
    _load_env()


@main.command()
@click.argument("source", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", type=click.Path(path_type=Path), default=None)
@click.option("--format", "output_format", type=click.Choice(["md", "json"]), default="md")
@click.option(
    "--fallback-provider",
    type=click.Choice(["mistral", "openai", "gemini", "anthropic", "ollama"]),
    default=None,
)
@click.option("--vlm-preset", default=None)
@click.option("--config", "config_path", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--no-fallback", is_flag=True, default=False)
@click.option("-v", "--verbose", is_flag=True, default=False)
@click.option("-q", "--quiet", is_flag=True, default=False)
def convert_cmd(
    source: Path,
    output: Path | None,
    output_format: str,
    fallback_provider: str | None,
    vlm_preset: str | None,
    config_path: Path | None,
    no_fallback: bool,
    verbose: bool,
    quiet: bool,
):
    """Convert a document to Markdown."""
    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    elif not quiet:
        logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    overrides: dict = {}
    if fallback_provider is not None:
        overrides["fallback_provider"] = fallback_provider
    if vlm_preset is not None:
        overrides["vlm_preset"] = vlm_preset
    if no_fallback:
        overrides["fallback_enabled"] = False

    config = PipelineConfig.from_sources(
        cli_overrides=overrides if overrides else None,
        yaml_path=config_path,
    )

    try:
        result = convert(source, config)
    except UnsupportedFormatError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if output_format == "json":
        content = json.dumps(result.to_dict(), indent=2)
    else:
        content = result.markdown

    if output:
        output.write_text(content, encoding="utf-8")
        if not quiet:
            click.echo(f"Written to {output}", err=True)
            if verbose and result.warnings:
                for w in result.warnings:
                    click.echo(f"Warning: {w}", err=True)
    else:
        click.echo(content)

    if verbose:
        click.echo(
            f"Pipeline: {result.pipeline_used} | "
            f"Pages: {result.page_count or 'N/A'} | "
            f"Time: {result.processing_time_seconds:.2f}s | "
            f"Escalated: {result.escalated}",
            err=True,
        )


@main.command()
@click.argument("source", type=click.Path(exists=True, path_type=Path))
def info(source: Path):
    """Show detected MIME type, page count, and recommended processing path."""
    mime = detect_mime(source)
    path = classify(source)

    from docprep.utils.images import get_page_count

    pages = get_page_count(source)

    click.echo(f"File:      {source}")
    click.echo(f"MIME type: {mime}")
    click.echo(f"Pages:     {pages or 'N/A'}")
    click.echo(f"Path:      {path.value}")


if __name__ == "__main__":
    main()
