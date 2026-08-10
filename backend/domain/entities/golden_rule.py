"""
Entite GoldenRule — couche Domain.

Representation d'une des 10 Golden Rules de gouvernance Sofrecom.
Une Golden Rule regroupe une ou plusieurs SousRegle qui decrivent
comment la verifier concretement selon le type de fichier.

Aucune dependance externe : uniquement la stdlib Python.
"""

from dataclasses import dataclass, field
from typing import List

from .sous_regle import SousRegle


@dataclass
class GoldenRule:
    """Une regle de gouvernance et l'ensemble de ses sous-regles."""

    # Identifiant numerique de la regle, de 1 a 10.
    id: int

    # Nom court de la regle.
    # Exemple : "Secrets en clair"
    nom: str

    # Description complete de ce que la regle exige du projet.
    description: str

    # Gravite d'une violation de cette regle.
    # Valeurs attendues : "critique" (-15 points) ou "warning" (-5 points)
    severite: str

    # Liste des SousRegle qui declinent la regle par type de fichier / outil.
    # Vide par defaut : les sous-regles sont ajoutees a la construction.
    sous_regles: List[SousRegle] = field(default_factory=list)
