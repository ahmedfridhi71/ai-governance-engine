"""
Entite Rapport — couche Domain.

Resultat final d'une analyse de conformite sur un depot Git :
le score obtenu, le statut associe et la liste complete des violations.

C'est l'objet retourne par l'API et persiste en base.

Aucune dependance externe : uniquement la stdlib Python.
"""

from dataclasses import dataclass, field
from typing import Dict, List

from .violation import Violation


@dataclass
class Rapport:
    """Rapport de conformite complet pour un depot analyse."""

    # URL du depot Git analyse.
    # Exemple : "https://github.com/sofrecom/mon-projet"
    repo_url: str

    # Score de conformite sur 100, calcule a partir des violations.
    # 100 au depart, -15 par violation critique, -5 par warning, borne a 0.
    score: int = field(default=100)

    # Statut derive du score.
    # Valeurs attendues : "conforme" (>= 80), "attention" (50-79),
    # "non conforme" (< 50)
    statut: str = field(default="")

    # Liste des Violation detectees, apres deduplication.
    violations: List[Violation] = field(default_factory=list)

    # Nombre total de fichiers trouves dans le depot clone.
    total_fichiers: int = field(default=0)

    # Nombre de fichiers reellement analyses, apres filtrage
    # des fichiers ignores (node_modules, .git, binaires...).
    fichiers_analyses: int = field(default=0)

    # Date et heure de l'analyse au format ISO 8601.
    # Exemple : "2026-08-06T14:32:05"
    date_analyse: str = field(default="")

    # Synthese chiffree de l'analyse.
    # Clefs attendues : "critiques", "warnings", "conformes"
    # Exemple : {"critiques": 3, "warnings": 7, "conformes": 5}
    resume: Dict[str, int] = field(default_factory=dict)
