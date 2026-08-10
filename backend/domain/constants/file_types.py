"""
Classification des fichiers — couche Domain.

Determine la categorie d'un fichier, qui decide des analyseurs utilises :
  - "devops" : manifests K8s/Helm, Terraform, Dockerfile, pipelines CI/CD
               -> Checkov + LLM
  - "code"   : sources applicatives, fichiers de dependances et de config
               -> analyseur Python custom + LLM
  - "autre"  : tout le reste (nginx.conf, Makefile, .sql, ...)
               -> LLM uniquement

Aucune dependance externe : uniquement la stdlib Python.
"""

from typing import Dict

# Extensions identifiant un fichier d'infrastructure ou de pipeline.
EXTENSIONS_DEVOPS: Dict[str, str] = {
    ".yaml": "Kubernetes/Helm/CI-CD manifest",
    ".yml": "Kubernetes/Helm/CI-CD manifest",
    ".tf": "Terraform infrastructure",
}

# Noms exacts (ou repertoires) identifiant un fichier DevOps.
NOMS_DEVOPS: Dict[str, str] = {
    "Dockerfile": "Docker image definition",
    ".gitlab-ci.yml": "GitLab CI/CD pipeline",
    ".github": "GitHub Actions pipeline",
}

# Extensions identifiant du code source ou de la configuration applicative.
EXTENSIONS_CODE: Dict[str, str] = {
    ".py": "Python source code",
    ".js": "JavaScript source code",
    ".ts": "TypeScript source code",
    ".java": "Java source code",
    ".go": "Go source code",
    ".rb": "Ruby source code",
    ".php": "PHP source code",
    ".cs": "C# source code",
    ".env": "Environment variables",
    ".json": "JSON configuration",
    ".toml": "TOML configuration",
    ".properties": "Java properties",
    ".xml": "XML configuration",
    ".ini": "INI configuration",
}

# Noms exacts identifiant un fichier de dependances, de doc ou de licence.
NOMS_CODE: Dict[str, str] = {
    "requirements.txt": "Python dependencies",
    "package.json": "Node.js dependencies",
    "pom.xml": "Maven dependencies",
    "build.gradle": "Gradle dependencies",
    "Gemfile": "Ruby dependencies",
    "go.mod": "Go dependencies",
    "README.md": "Project documentation",
    "README.rst": "Project documentation",
    "LICENSE": "Project license",
    "LICENCE": "Project license",
}


def detecter_type(nom: str, extension: str, contenu: str) -> str:
    """Classe un fichier en "devops", "code" ou "autre".

    L'ordre des tests est important : le nom exact prime sur l'extension,
    et l'inspection du contenu permet de rattraper les manifests K8s ou
    les pipelines CI/CD portant un nom quelconque (ex: "deploy-prod.yaml"
    ou "ci.yml" a la racine).

    Args:
        nom: nom du fichier seul, extension comprise.
        extension: extension avec le point (ex: ".yaml"), vide si absente.
        contenu: contenu textuel brut du fichier (peut etre vide).

    Returns:
        "devops", "code" ou "autre".
    """
    # 1. Nom exact reconnu comme DevOps (Dockerfile, .gitlab-ci.yml, ...)
    if nom in NOMS_DEVOPS:
        return "devops"

    # 2. Extension d'infrastructure (.yaml, .yml, .tf)
    if extension in EXTENSIONS_DEVOPS:
        return "devops"

    # 3. Signature d'un manifest Kubernetes / Helm dans le contenu
    if "kind:" in contenu or "apiVersion:" in contenu:
        return "devops"

    # 4. Signature d'un pipeline CI/CD dans le contenu
    if "stages:" in contenu or "jobs:" in contenu:
        return "devops"

    # 5. Nom exact reconnu comme fichier de code / dependances / doc
    if nom in NOMS_CODE:
        return "code"

    # 6. Extension de code source ou de configuration applicative
    if extension in EXTENSIONS_CODE:
        return "code"

    # 7. Non reconnu : analyse par le LLM uniquement
    return "autre"
