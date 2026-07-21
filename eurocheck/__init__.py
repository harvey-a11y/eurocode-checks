"""eurocheck: educational EC2/EC3 member design checks.

A small, honest library covering a defined subset of EN 1992-1-1
(concrete) and EN 1993-1-1 (steel) member checks with UK National Annex
parameters. Every result is traceable to a hand calculation in
VALIDATION.md. Not a certified design package.
"""

from . import ec2_beam, ec3_member
from .sections import Section, get_section, list_sections

__version__ = "0.1.0"

__all__ = [
    "Section",
    "get_section",
    "list_sections",
    "ec2_beam",
    "ec3_member",
    "__version__",
]
