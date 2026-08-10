"""
Couche Domain — coeur metier de l'AI Governance Engine.

Contient uniquement des entites et des constantes, sans aucune
dependance externe ni acces au reseau, a la base ou au systeme de fichiers.

    from domain import GoldenRule, Violation, Rapport
"""

from .entities import (
    SousRegle,
    GoldenRule,
    FichierProjet,
    Violation,
    Rapport,
)

__all__ = [
    "SousRegle",
    "GoldenRule",
    "FichierProjet",
    "Violation",
    "Rapport",
]
