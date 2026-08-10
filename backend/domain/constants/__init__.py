"""
Constantes du Domain.

Regroupe les imports pour permettre :
    from domain.constants import GOLDEN_RULES, detecter_type, doit_ignorer
"""

from .fichiers_ignores import (
    DOSSIERS_IGNORES,
    EXTENSIONS_IGNOREES,
    FICHIERS_IGNORES,
    doit_ignorer,
)
from .file_types import (
    EXTENSIONS_DEVOPS,
    NOMS_DEVOPS,
    EXTENSIONS_CODE,
    NOMS_CODE,
    detecter_type,
)
from .checkov_mapping import CHECKOV_MAPPING, NON_MAPPE, mapper_check_id
from .golden_rules import GOLDEN_RULES, get_rule_by_id

__all__ = [
    # fichiers_ignores
    "DOSSIERS_IGNORES",
    "EXTENSIONS_IGNOREES",
    "FICHIERS_IGNORES",
    "doit_ignorer",
    # file_types
    "EXTENSIONS_DEVOPS",
    "NOMS_DEVOPS",
    "EXTENSIONS_CODE",
    "NOMS_CODE",
    "detecter_type",
    # checkov_mapping
    "CHECKOV_MAPPING",
    "NON_MAPPE",
    "mapper_check_id",
    # golden_rules
    "GOLDEN_RULES",
    "get_rule_by_id",
]
