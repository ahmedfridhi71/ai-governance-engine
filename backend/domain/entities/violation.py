"""
Entite Violation — couche Domain.

Representation d'un manquement a une Golden Rule detecte dans un fichier
du projet analyse.

Une Violation est produite par un analyseur (Checkov, Python custom ou LLM)
avec les champs factuels renseignes, puis enrichie plus tard par le LLM
qui remplit "explication" et "correction".

Aucune dependance externe : uniquement la stdlib Python.
"""

from dataclasses import dataclass, field


@dataclass
class Violation:
    """Un probleme de conformite detecte dans un fichier precis."""

    # Chemin du fichier concerne, relatif a la racine du repo clone.
    # Exemple : "backend/infrastructure/database/mongodb_client.py"
    fichier: str

    # Identifiant de la Golden Rule violee, de 1 a 10.
    regle_id: int

    # Nom court de la Golden Rule violee.
    # Exemple : "Secrets en clair"
    regle_nom: str

    # Gravite de la violation, heritee de la Golden Rule.
    # Valeurs attendues : "critique" (-15 points) ou "warning" (-5 points)
    severite: str

    # Description factuelle du probleme detecte.
    # Exemple : "mot de passe en clair : password = 'admin123'"
    probleme: str

    # Explication pedagogique du risque, redigee par le LLM.
    # Vide au depart : remplie lors de l'etape d'enrichissement.
    explication: str = field(default="")

    # Correction proposee (extrait de code ou marche a suivre), redigee par le LLM.
    # Vide au depart : remplie lors de l'etape d'enrichissement.
    correction: str = field(default="")

    # Analyseur a l'origine de la detection.
    # Valeurs attendues : "checkov", "python" ou "llm"
    source: str = field(default="")

    # Numero de ligne du probleme dans le fichier.
    # -1 lorsque la ligne exacte est inconnue (detection au niveau du fichier).
    ligne: int = field(default=-1)
