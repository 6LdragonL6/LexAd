"""File and object storage abstraction.

Encapsulate file system operations, S3-compatible object storage, etc.
Provides a uniform interface regardless of storage backend.
"""

from __future__ import annotations


class BaseStorage:
    """Base class for storage backends."""
    pass
