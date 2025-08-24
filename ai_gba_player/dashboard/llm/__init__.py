"""
LLM Module - Modular LLM Client Implementation

Splits the large LLMClient into focused, maintainable modules:
- client.py: Core LLMClient class (~800 lines)
- providers.py: Provider-specific API implementations (~600 lines) 
- image_processing.py: Image enhancement and processing (~400 lines)
- context_builder.py: Prompt context building logic (~500 lines)

This follows the coding convention of keeping files under 2000 lines
and organizing code by clear functional boundaries.
"""

# Import components from the refactored modules
from .image_processing import ImageProcessor
from .context_builder import ContextBuilder

# For backward compatibility, still expose the original LLMClient
# from the main dashboard directory
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dashboard.llm_client import LLMClient

__all__ = ['LLMClient', 'ImageProcessor', 'ContextBuilder']