"""
MCP-Style Tools

This package contains minimal MCP-style tools that provide
deterministic computation capabilities to LLM agents.

These tools demonstrate how to extend LLM capabilities beyond
prompting by delegating precise calculations to external tools.
"""

from .date_calculator import calculate_days_between

__all__ = ['calculate_days_between']
