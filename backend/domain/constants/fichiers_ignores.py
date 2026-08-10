"""
Listes noires du Crawler — couche Domain.

Definit ce que le Crawler ne doit jamais lire ni analyser :
dossiers techniques, fichiers binaires et fichiers generes.

Objectif : eviter de perdre du temps (et des tokens LLM) sur des
fichiers sans valeur de gouvernance, et ne jamais tenter de decoder
du binaire en texte.

Aucune dependance externe : uniquement la stdlib Python.
"""

from typing import List

# Dossiers techniques a ne jamais parcourir.
# Le test se fait sur chaque segment du chemin : si l'un d'eux figure
# dans cette liste, tout le sous-arbre est ignore.
DOSSIERS_IGNORES: List[str] = [
    ".git",             # metadonnees Git
    "node_modules",     # dependances Node.js
    "__pycache__",      # bytecode Python
    "venv",             # environnement virtuel Python
    ".venv",            # environnement virtuel Python (variante)
    "env",              # environnement virtuel Python (variante)
    ".idea",            # config IDE JetBrains
    ".vscode",          # config IDE VS Code
    "dist",             # artefacts de build
    "build",            # artefacts de build
    "target",           # artefacts de build Maven / Rust
    ".next",            # artefacts de build Next.js
    "coverage",         # rapports de couverture
    ".tox",             # environnements Tox
    ".eggs",            # artefacts setuptools
    "htmlcov",          # rapports de couverture HTML
    ".pytest_cache",    # cache Pytest
]

# Extensions de fichiers binaires ou compiles : illisibles en texte.
# Toujours comparees en minuscules, point inclus.
EXTENSIONS_IGNOREES: List[str] = [
    # images
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    # audio / video
    ".mp4", ".mp3", ".avi", ".mov",
    # documents bureautiques
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    # archives
    ".zip", ".tar", ".gz", ".rar",
    # binaires et bibliotheques
    ".exe", ".bin", ".dll", ".so", ".dylib",
    # code compile
    ".pyc", ".class", ".o", ".a",
    # verrous de dependances (generes, tres volumineux)
    ".lock",
]

# Fichiers precis a ignorer, identifies par leur nom exact.
FICHIERS_IGNORES: List[str] = [
    ".DS_Store",            # metadonnees macOS
    "Thumbs.db",            # metadonnees Windows
    ".gitignore",           # config Git
    ".gitattributes",       # config Git
    "package-lock.json",    # verrou de dependances npm
    "yarn.lock",            # verrou de dependances Yarn
    "poetry.lock",          # verrou de dependances Poetry
    "Pipfile.lock",         # verrou de dependances Pipenv
]


def doit_ignorer(chemin: str, nom: str, extension: str) -> bool:
    """Indique si un fichier doit etre exclu de l'analyse.

    Trois motifs d'exclusion, testes dans l'ordre :
      1. le fichier se trouve dans un dossier de DOSSIERS_IGNORES
      2. son nom exact figure dans FICHIERS_IGNORES
      3. son extension figure dans EXTENSIONS_IGNOREES

    Args:
        chemin: chemin du fichier (absolu ou relatif).
        nom: nom du fichier seul, extension comprise (ex: "main.py").
        extension: extension avec le point (ex: ".py"), vide si absente.

    Returns:
        True si le fichier doit etre ignore, False s'il doit etre analyse.
    """
    # 1. Un des dossiers traverses est-il sur liste noire ?
    #    On normalise les separateurs pour traiter Windows et Unix pareil.
    segments = chemin.replace("\\", "/").split("/")
    for dossier in DOSSIERS_IGNORES:
        if dossier in segments:
            return True

    # 2. Nom de fichier exact sur liste noire ?
    if nom in FICHIERS_IGNORES:
        return True

    # 3. Extension binaire ou generee ? (comparaison insensible a la casse)
    if extension.lower() in EXTENSIONS_IGNOREES:
        return True

    return False
