"""
Utility functions for analyzers and reporter in CQIA.

Provides helpers for hashing, normalization, text chunking,
and safe file reading.
"""

import hashlib
import re
import json
from typing import List, Tuple


def sha256_text(text: str) -> str:
    """
    Compute SHA256 hex digest of input text.

    Args:
        text: Input string.
    Returns:
        str: Hexadecimal digest.

    Example:
        >>> sha256_text("hello")
        '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824'
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_source(source: str) -> str:
    """
    Normalize source code for comparison / duplication detection.

    Operations:
    - Strip leading/trailing whitespace
    - Collapse multiple whitespace into single space
    - Remove single-line comments (# for Python, // for JS)
    - Remove block comments (/* ... */ for JS)

    Args:
        source: Source code string.
    Returns:
        str: Normalized source.

    Example:
        >>> normalize_source("  # Comment\\nprint(  42 )  ")
        'print( 42 )'
    """
    text = source.strip()
    # Remove Python comments
    text = re.sub(r"#.*", "", text)
    # Remove JS single-line comments
    text = re.sub(r"//.*", "", text)
    # Remove JS block comments
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def chunk_text(text: str, n: int = 1000) -> List[str]:
    """
    Split text into overlapping chunks of size <= n.

    Overlap is 100 characters between consecutive chunks.

    Args:
        text: Input string.
        n: Maximum chunk size (default=1000).
    Returns:
        List[str]: List of chunked strings.

    Example:
        >>> len(chunk_text("a" * 2500, 1000))
        3
    """
    if not text:
        return []
    overlap = 100
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + n, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


def safe_read_text(path: str) -> str:
    """
    Safely read file content as UTF-8 text, ignoring errors.

    Args:
        path: File path.
    Returns:
        str: File content or empty string if not readable.

    Example:
        >>> content = safe_read_text("nonexistent.txt")
        >>> content == ""
        True
    """
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""
