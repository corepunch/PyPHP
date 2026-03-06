"""
pyphp — PHP-style template renderer for Python.

Public API:
    Context       — holds template variables and filters
    render        — render a PHP template string
    render_file   — render a PHP template file
    tokenize      — parse a template into a token list
    E             — XML element wrapper for dot-access of attributes
    php_to_python — convert a PHP code snippet to Python
    PHPError      — exception raised when PHP execution fails
"""

from .renderer import Context, render, render_file, tokenize, E, PHPError
from .preprocessor import php_to_python

__all__ = [
    'Context',
    'render',
    'render_file',
    'tokenize',
    'E',
    'php_to_python',
    'PHPError',
]
