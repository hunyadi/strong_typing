"""
Type-safe data interchange for Python data classes.

Provides auxiliary services for working with Python type annotations, converting typed data to and from JSON,
and generating a JSON schema for a complex type.
"""

from .auxiliary import *
from .core import *
from .inspection import *
from .schema import *
from .serialization import *
