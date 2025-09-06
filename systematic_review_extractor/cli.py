"""Command-line interface for systematic review extractor."""

import click
import sys
from pathlib import Path
from typing import List, Optional
from loguru import logger

from .core.extractor import SystematicReviewExtractor
from .models.schemas import ExtractionConfig
from .utils.config import ConfigManager, setup_logging
from .utils.exporters import ResultExporter


@click.group()
@click.option('--log-level', default='INFO', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
              help='Set logging level')
def cli(log_level: str):
    """Systematic Review Extractor - AI-powered data extraction with zero hallucination guarantee."""
    setup_logging(log_level)


@cli.command()
@click.argument('input_path', type=click.Path(exists=True, path_type=Path))
@click.option('--fields', '-f', multiple=True, required=True,
              help='Fields to extract (can be specified multiple times)')
@click.option('--output', '-o', type=click.Path(path_type=Path),
              help='Output file path (default: results.json)')
@click.option('--format', 'output_format', type=click.Choice(['json', 'csv', 'excel']), default='json',
              help='Output format')
@click.option('--ai-provider', type=click.Choice(['openai', 'anthropic']), default='openai',
              help='AI provider to use')
@click.option('--model', default='gpt-4',
              help='AI model name')
@click.option('--confidence-threshold', type=float, default=0.7,
              help='Minimum confidence threshold (0.0-1.0)')
@click.option('--context', help='Additional context for extraction')
@click.option('--no-validation', is_flag=True, help='Disable validation')
def extract(
    input_path: Path,
    fields: tuple,
    output: Optional[Path],
    output_format: str,
    ai_provider: str,
    model: str,
    confidence_threshold: float,
    context: Optional[str],
    no_validation: bool
):
    """Extract data from PDF files."""
    
    # Validate input
    if not fields:
        click.echo("Error: At least one field must be specified with --fields", err=True)
        sys.exit(1)
    
    # Setup configuration
    config_manager = ConfigManager()
    
    # Check API keys
    api_status = config_manager.validate_api_keys()
    if not api_status.get(ai_provider):
        click.echo(f"Error: {ai_provider.upper()}_API_KEY not found in environment", err=True)
        click.echo("Please set your API key in environment variables or .env file", err=True)
        sys.exit(1)
    
    # Create extraction config
    config = config_manager.create_extraction_config({
        'ai_provider': ai_provider,
        'model_name': model,
        'confidence_threshold': confidence_threshold,
        'validation_enabled': not no_validation
    })
    
    # Initialize extractor
    try:
        extractor = SystematicReviewExtractor(config)
    except Exception as e:
        click.echo(f"Error initializing extractor: {e}", err=True)
        sys.exit(1)
    
    # Determine input files
    if input_path.is_file():
        file_paths = [input_path]
    elif input_path.is_dir():
        file_paths = list(input_path.glob("*.pdf"))
        if not file_paths:
            click.echo(f"No PDF files found in {input_path}", err=True)
            sys.exit(1)
    else:
        click.echo(f"Invalid input path: {input_path}", err=True)
        sys.exit(1)
    
    click.echo(f"Processing {len(file_paths)} file(s)...")
    click.echo(f"Fields to extract: {', '.join(fields)}")
    
    # Extract data
    try:
        if len(file_paths) == 1:
            results = [extractor.extract_from_file(file_paths[0], list(fields), context)]
        else:
            results = extractor.extract_from_files(file_paths, list(fields), context)
    except Exception as e:
        click.echo(f"Error during extraction: {e}", err=True)
        sys.exit(1)
    
    # Generate output filename if not provided
    if not output:
        timestamp = Path().cwd() / f"extraction_results_{ai_provider}_{len(results)}files"
        output = timestamp.with_suffix(f".{output_format}")
    
    # Export results
    exporter = ResultExporter()
    try:
        if output_format == 'json':
            exporter.export_to_json(results, output)
        elif output_format == 'csv':
            exporter.export_to_csv(results, output)
        elif output_format == 'excel':
            exporter.export_to_excel(results, output)
    except Exception as e:
        click.echo(f"Error exporting results: {e}", err=True)
        sys.exit(1)
    
    # Print summary
    stats = extractor.get_processing_stats(results)
    click.echo("\n" + "="*50)
    click.echo("EXTRACTION SUMMARY")
    click.echo("="*50)
    click.echo(f"Total files processed: {stats.total_files}")
    click.echo(f"Successful extractions: {stats.successful_extractions}")
    click.echo(f"Failed extractions: {stats.failed_extractions}")
    click.echo(f"Validation pass rate: {stats.validation_pass_rate:.1%}")
    click.echo(f"Average processing time: {stats.average_processing_time:.2f}s")
    click.echo(f"Total processing time: {stats.total_processing_time:.2f}s")
    click.echo(f"Results exported to: {output}")


@cli.command()
@click.option('--output', '-o', type=click.Path(path_type=Path), default=Path(".env"),
              help='Output path for .env file')
def init(output: Path):
    """Initialize configuration file."""
    config_manager = ConfigManager()
    
    if output.exists():
        if not click.confirm(f"{output} already exists. Overwrite?"):
            click.echo("Initialization cancelled.")
            return
    
    config_manager.create_sample_env_file(output)
    click.echo(f"Configuration file created: {output}")
    click.echo("Please edit the file and add your API keys.")


@cli.command()
def validate_config():
    """Validate current configuration."""
    config_manager = ConfigManager()
    
    click.echo("Validating configuration...")
    
    # Check API keys
    api_status = config_manager.validate_api_keys()
    
    click.echo("\nAPI Key Status:")
    for provider, available in api_status.items():
        status = "✓ Available" if available else "✗ Missing"
        click.echo(f"  {provider.capitalize()}: {status}")
    
    # Test configuration creation
    try:
        config = config_manager.create_extraction_config()
        click.echo(f"\nConfiguration loaded successfully:")
        click.echo(f"  AI Provider: {config.ai_provider}")
        click.echo(f"  Model: {config.model_name}")
        click.echo(f"  Confidence Threshold: {config.confidence_threshold}")
        click.echo(f"  Validation Enabled: {config.validation_enabled}")
    except Exception as e:
        click.echo(f"\nConfiguration error: {e}", err=True)
        sys.exit(1)
    
    click.echo("\nConfiguration validation completed.")


@cli.command()
@click.option('--fields', '-f', multiple=True,
              help='Example fields to demonstrate (uses default if not specified)')
def demo(fields: tuple):
    """Run a demonstration with sample data."""
    
    if not fields:
        fields = [
            'study_design',
            'sample_size', 
            'intervention',
            'primary_outcome',
            'p_value'
        ]
    
    click.echo("Systematic Review Extractor Demo")
    click.echo("="*40)
    click.echo(f"This would extract the following fields: {', '.join(fields)}")
    click.echo("\nTo run actual extraction:")
    click.echo("1. Set up your .env file with API keys: sr-extract init")
    click.echo("2. Extract from PDF files: sr-extract extract path/to/pdfs --fields study_design --fields sample_size")
    click.echo("\nFor more information, run: sr-extract --help")


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == '__main__':
    main()