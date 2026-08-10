"""
Entites du Domain.

Regroupe les imports pour permettre :
    from domain.entities import GoldenRule, Violation, Rapport

Ordre de declaration = ordre des dependances entre entites :
    SousRegle -> GoldenRule -> FichierProjet -> Violation -> Rapport
"""

from .sous_regle import SousRegle
from .golden_rule import GoldenRule
from .fichier_projet import FichierProjet
from .violation import Violation
from .rapport import Rapport

__all__ = [
    "SousRegle",
    "GoldenRule",
    "FichierProjet",
    "Violation",
    "Rapport",
]
