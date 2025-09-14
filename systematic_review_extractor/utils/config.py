"""Configuration management utilities."""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger
from dotenv import load_dotenv

from ..models.schemas import ExtractionConfig


class ConfigManager:
    """Manage configuration for the systematic review extractor."""
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Optional path to configuration file
        """
        self.config_file = config_file
        self._load_environment()
    
    def _load_environment(self):
        """Load environment variables from .env file."""
        # Look for .env file in current directory or parent directories
        env_file = Path(".env")
        if not env_file.exists():
            env_file = Path("../.env")
        
        if env_file.exists():
            load_dotenv(env_file)
            logger.info(f"Loaded environment from {env_file}")
    
    def create_extraction_config(
        self, 
        overrides: Optional[Dict[str, Any]] = None
    ) -> ExtractionConfig:
        """
        Create extraction configuration from environment and overrides.
        
        Args:
            overrides: Dictionary of configuration overrides
            
        Returns:
            ExtractionConfig object
        """
        # Default configuration
        config_dict = {
            "ai_provider": os.getenv("AI_PROVIDER", "openai"),
            "model_name": os.getenv("MODEL_NAME", "gpt-4"),
            "max_tokens": int(os.getenv("MAX_TOKENS", "4000")),
            "temperature": float(os.getenv("TEMPERATURE", "0.1")),
            "validation_enabled": os.getenv("VALIDATION_ENABLED", "true").lower() == "true",
            "confidence_threshold": float(os.getenv("CONFIDENCE_THRESHOLD", "0.7")),
            "retry_attempts": int(os.getenv("RETRY_ATTEMPTS", "3"))
        }
        
        # Apply overrides
        if overrides:
            config_dict.update(overrides)
        
        # Validate AI provider
        if config_dict["ai_provider"] == "openai":
            if not os.getenv("OPENAI_API_KEY"):
                logger.warning("OPENAI_API_KEY not found in environment")
        elif config_dict["ai_provider"] == "anthropic":
            if not os.getenv("ANTHROPIC_API_KEY"):
                logger.warning("ANTHROPIC_API_KEY not found in environment")
            # Set default model for Anthropic
            if config_dict["model_name"] == "gpt-4":
                config_dict["model_name"] = "claude-3-sonnet-20240229"
        
        return ExtractionConfig(**config_dict)
    
    def validate_api_keys(self) -> Dict[str, bool]:
        """
        Validate that required API keys are present.
        
        Returns:
            Dictionary mapping provider names to availability status
        """
        api_status = {
            "openai": bool(os.getenv("OPENAI_API_KEY")),
            "anthropic": bool(os.getenv("ANTHROPIC_API_KEY"))
        }
        
        logger.info(f"API key status: {api_status}")
        return api_status
    
    def get_sample_config(self) -> str:
        """
        Get a sample configuration file content.
        
        Returns:
            String containing sample configuration
        """
        return """# Systematic Review Extractor Configuration

# AI Provider Settings
AI_PROVIDER=openai  # or 'anthropic'
MODEL_NAME=gpt-4    # or 'claude-3-sonnet-20240229' for Anthropic
MAX_TOKENS=4000
TEMPERATURE=0.1

# API Keys (required)
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Extraction Settings
VALIDATION_ENABLED=true
CONFIDENCE_THRESHOLD=0.7
RETRY_ATTEMPTS=3

# Logging Level
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
"""
    
    def create_sample_env_file(self, file_path: Path = Path(".env")):
        """
        Create a sample .env file.
        
        Args:
            file_path: Path where to create the .env file
        """
        if file_path.exists():
            logger.warning(f"{file_path} already exists. Skipping creation.")
            return
        
        with open(file_path, 'w') as f:
            f.write(self.get_sample_config())
        
        logger.info(f"Created sample configuration file: {file_path}")
        logger.info("Please edit the file and add your API keys.")


def setup_logging(level: str = "INFO"):
    """
    Set up logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Remove default logger
    logger.remove()
    
    # Add console logger with format
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=level,
        colorize=True
    )
    
    # Add file logger
    logger.add(
        "systematic_review_extractor.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=level,
        rotation="10 MB",
        retention="30 days"
    )