"""
AI Integration package
"""
from .claude_client import ClaudeClient
from .prompts import PromptManager

__all__ = ['ClaudeClient', 'PromptManager']
