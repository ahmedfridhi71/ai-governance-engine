"""
Entite FichierProjet — couche Domain.

Representation d'un fichier du projet clone, tel que remonte
par le Crawler puis transmis aux analyseurs.

La categorie "type_fichier" determine quels analyseurs seront utilises :
  - "devops" : .yaml .yml .tf Dockerfile fichiers CI/CD  -> Checkov + LLM
  - "code"   : .py .js .java .env requirements.txt        -> Python custom + LLM
  - "autre"  : nginx.conf Makefile .sql ...               -> LLM uniquement

Aucune dependance externe : uniquement la stdlib Python.
"""

from dataclasses import dataclass, field


@dataclass
class FichierProjet:
    """Un fichier du projet analyse, avec son contenu brut."""

    # Chemin absolu du fichier sur le disque, dans le repo clone.
    # Exemple : "/tmp/projet_123/backend/main.py"
    chemin: str

    # Nom du fichier seul, extension comprise.
    # Exemple : "main.py"
    nom: str

    # Categorie d'analyse du fichier.
    # Valeurs attendues : "devops", "code" ou "autre"
    type_fichier: str

    # Contenu textuel brut du fichier.
    # Vide par defaut : rempli a la lecture, reste vide si la lecture echoue.
    contenu: str = field(default="")

    # Taille du fichier en octets.
    # 0 par defaut, sert notamment a decider du decoupage en chunks pour le LLM.
    taille: int = field(default=0)
