"""
Entite SousRegle — couche Domain.

Une sous-regle decrit COMMENT verifier une Golden Rule
sur un type de fichier precis, et avec quel outil.

Exemple :
    Golden Rule 1 (Secrets en clair) se decline en plusieurs sous-regles :
      - fichier .env    verifie par "python"  avec le pattern r"(?i)password\\s*="
      - fichier .tf     verifie par "checkov" avec le pattern "CKV_SECRET_*"
      - fichier .py     verifie par "llm"     avec un pattern en langage naturel

Aucune dependance externe : uniquement la stdlib Python.
"""

from dataclasses import dataclass


@dataclass
class SousRegle:
    """Regle de verification unitaire appliquee a un type de fichier."""

    # Type de fichier cible sur lequel la sous-regle s'applique.
    # Exemples : "python", "yaml", "tf", "dockerfile", "js", "env", "*"
    type_fichier: str

    # Outil charge d'executer la verification.
    # Valeurs attendues : "checkov", "python" ou "llm"
    outil: str

    # Description lisible du probleme recherche.
    # Exemple : "mot de passe ecrit en clair dans le code"
    description: str

    # Motif de detection.
    # - Pour l'outil "python"  : une expression reguliere (regex)
    # - Pour l'outil "checkov" : un identifiant de check (ex: "CKV_AWS_20")
    # - Pour l'outil "llm"     : une consigne en langage naturel
    pattern: str
