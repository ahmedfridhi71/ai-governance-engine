"""
Les 10 Golden Rules — couche Domain.

Referentiel complet de gouvernance : chaque regle porte sa severite
et la liste de ses sous-regles, qui decrivent comment la verifier
selon le type de fichier et avec quel outil.

Conventions de pattern selon l'outil :
  - outil "python"  : soit une regex, soit une directive de l'analyseur
                      custom :
                        "ABSENT:<texte>"          -> le texte doit etre present
                        "ABSENT_TOUS:<a>,<b>"     -> au moins un doit etre present
                        "CLE_ABSENTE:<cle>"       -> cle JSON obligatoire
                        "FICHIER_ABSENT:<a>,<b>"  -> au moins un fichier requis
                        "TAILLE_MINIMALE:<n>"     -> taille minimale en octets
  - outil "checkov" : un identifiant (ou prefixe) de check Checkov
  - outil "llm"     : une consigne en langage naturel

Bareme : violation "critique" = -15 points, "warning" = -5 points.

Aucune dependance externe : uniquement la stdlib Python.
"""

from typing import List, Optional

from ..entities import GoldenRule, SousRegle

# --------------------------------------------------------------------------
# Regle 1 — Secrets en clair
# --------------------------------------------------------------------------
REGLE_1 = GoldenRule(
    id=1,
    nom="Secrets en clair",
    description=(
        "Aucun mot de passe, cle API, token ou certificat ne doit etre "
        "ecrit en dur dans le code, les manifests ou les fichiers de "
        "configuration. Les secrets doivent passer par un coffre-fort "
        "(Vault, Secret Manager) ou des variables d'environnement injectees."
    ),
    severite="critique",
    sous_regles=[
        SousRegle(
            type_fichier="python",
            outil="python",
            description="Mot de passe en clair",
            pattern=r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']{3,}["\']',
        ),
        SousRegle(
            type_fichier="env",
            outil="python",
            description="Clé API en clair dans .env",
            pattern=r'(?i)(api_key|apikey|secret|token)\s*=\s*\S+',
        ),
        SousRegle(
            type_fichier="yaml",
            outil="checkov",
            description="Secret en clair dans manifest",
            pattern="CKV_SECRET",
        ),
        SousRegle(
            type_fichier="tf",
            outil="checkov",
            description="Secret en clair dans Terraform",
            pattern="CKV_SECRET",
        ),
        SousRegle(
            type_fichier="complexe",
            outil="llm",
            description="Secrets avec noms custom ou encodés",
            pattern="Cherche des secrets avec des noms non standards ou encodés",
        ),
    ],
)

# --------------------------------------------------------------------------
# Regle 2 — Versionnement
# --------------------------------------------------------------------------
REGLE_2 = GoldenRule(
    id=2,
    nom="Versionnement",
    description=(
        "Toutes les dependances, images et modules doivent etre figes sur "
        "une version precise. Les tags flottants (latest, *, versions "
        "absentes) rendent les builds non reproductibles."
    ),
    severite="warning",
    sous_regles=[
        SousRegle(
            type_fichier="requirements",
            outil="python",
            description="Dépendance sans version fixe",
            pattern=r'^[a-zA-Z][a-zA-Z0-9_-]*\s*$',
        ),
        SousRegle(
            type_fichier="package.json",
            outil="python",
            description="Dépendance avec version flottante",
            pattern=r'"\s*\*\s*"|\"\s*latest\s*\"',
        ),
        SousRegle(
            type_fichier="yaml",
            outil="checkov",
            description="Image Docker avec tag latest",
            pattern="CKV_K8S_14",
        ),
        SousRegle(
            type_fichier="dockerfile",
            outil="checkov",
            description="Image de base sans version",
            pattern="CKV_DOCKER_7",
        ),
    ],
)

# --------------------------------------------------------------------------
# Regle 3 — Documentation
# --------------------------------------------------------------------------
REGLE_3 = GoldenRule(
    id=3,
    nom="Documentation",
    description=(
        "Le projet doit etre documente : un README utile a la racine, des "
        "docstrings sur les fonctions et une description dans les fichiers "
        "de dependances. Sans cela, la reprise du projet est couteuse."
    ),
    severite="warning",
    sous_regles=[
        SousRegle(
            type_fichier="readme",
            outil="python",
            description="README absent ou vide",
            pattern="TAILLE_MINIMALE:100",
        ),
        SousRegle(
            type_fichier="python",
            outil="python",
            description="Fonctions sans docstring",
            pattern=r'def \w+\([^)]*\):\s*\n\s*[^"\s]',
        ),
        SousRegle(
            type_fichier="package.json",
            outil="python",
            description="Description absente dans package.json",
            pattern="CLE_ABSENTE:description",
        ),
    ],
)

# --------------------------------------------------------------------------
# Regle 4 — Logs configures
# --------------------------------------------------------------------------
REGLE_4 = GoldenRule(
    id=4,
    nom="Logs configurés",
    description=(
        "L'application doit journaliser son activite via une bibliotheque "
        "de logging configuree, et non par des print / console.log. Sans "
        "logs exploitables, aucun incident n'est diagnosticable en production."
    ),
    severite="warning",
    sous_regles=[
        SousRegle(
            type_fichier="python",
            outil="python",
            description="Module logging non importé",
            pattern="ABSENT:import logging",
        ),
        SousRegle(
            type_fichier="js",
            outil="python",
            description="Logger non configuré en JS",
            pattern="ABSENT_TOUS:winston,morgan,pino,bunyan",
        ),
        SousRegle(
            type_fichier="complexe",
            outil="llm",
            description="Logging mal configuré ou insuffisant",
            pattern="Vérifie si le logging est correctement configuré",
        ),
    ],
)

# --------------------------------------------------------------------------
# Regle 5 — Gestion des erreurs
# --------------------------------------------------------------------------
REGLE_5 = GoldenRule(
    id=5,
    nom="Gestion des erreurs",
    description=(
        "Les erreurs doivent etre capturees et tracees explicitement. Les "
        "blocs except vides, les bare except et les promesses sans .catch "
        "masquent les pannes au lieu de les signaler."
    ),
    severite="warning",
    sous_regles=[
        SousRegle(
            type_fichier="python",
            outil="python",
            description="Absence de bloc try/except",
            pattern="ABSENT:try:",
        ),
        SousRegle(
            type_fichier="js",
            outil="python",
            description="Absence de gestion d'erreur en JS",
            pattern="ABSENT_TOUS:try {,.catch(",
        ),
        SousRegle(
            type_fichier="complexe",
            outil="llm",
            description="except vide ou trop large sans log",
            pattern="Cherche les except vides, bare except ou except sans logging",
        ),
    ],
)

# --------------------------------------------------------------------------
# Regle 6 — Securite des acces
# --------------------------------------------------------------------------
REGLE_6 = GoldenRule(
    id=6,
    nom="Sécurité des accès",
    description=(
        "Les acces doivent etre restreints par defaut : pas de mode DEBUG "
        "en production, pas de hote autorise en wildcard, pas de conteneur "
        "root ni d'escalade de privileges, et aucun endpoint sensible sans "
        "authentification."
    ),
    severite="critique",
    sous_regles=[
        SousRegle(
            type_fichier="env",
            outil="python",
            description="Mode DEBUG activé",
            pattern=r'(?i)DEBUG\s*=\s*(true|1|yes)',
        ),
        SousRegle(
            type_fichier="env",
            outil="python",
            description="ALLOWED_HOSTS trop permissif",
            pattern=r'(?i)ALLOWED_HOSTS\s*=\s*\*',
        ),
        SousRegle(
            type_fichier="yaml",
            outil="checkov",
            description="Absence de SecurityContext",
            pattern="CKV_K8S_30",
        ),
        SousRegle(
            type_fichier="complexe",
            outil="llm",
            description="Endpoint sans authentification ou injection SQL",
            pattern=(
                "Cherche les routes/endpoints sans protection "
                "d'authentification et les risques d'injection SQL"
            ),
        ),
    ],
)

# --------------------------------------------------------------------------
# Regle 7 — Disponibilite
# --------------------------------------------------------------------------
REGLE_7 = GoldenRule(
    id=7,
    nom="Disponibilité",
    description=(
        "Les charges de travail doivent survivre a la panne d'une instance : "
        "sondes liveness et readiness declarees, et plusieurs replicas pour "
        "les services exposes."
    ),
    severite="critique",
    sous_regles=[
        SousRegle(
            type_fichier="yaml",
            outil="checkov",
            description="Liveness probe absente",
            pattern="CKV_K8S_8",
        ),
        SousRegle(
            type_fichier="yaml",
            outil="checkov",
            description="Readiness probe absente",
            pattern="CKV_K8S_9",
        ),
        SousRegle(
            type_fichier="yaml",
            outil="checkov",
            description="Replicas insuffisants",
            pattern="CKV_K8S_20",
        ),
    ],
)

# --------------------------------------------------------------------------
# Regle 8 — Limite des ressources
# --------------------------------------------------------------------------
REGLE_8 = GoldenRule(
    id=8,
    nom="Limite des ressources",
    description=(
        "Chaque conteneur doit declarer ses requests et limits CPU/memoire. "
        "Sans plafond, un seul pod peut saturer un noeud et faire tomber "
        "les autres charges de travail."
    ),
    severite="critique",
    sous_regles=[
        SousRegle(
            type_fichier="yaml",
            outil="checkov",
            description="CPU limits absent",
            pattern="CKV_K8S_11",
        ),
        SousRegle(
            type_fichier="yaml",
            outil="checkov",
            description="Memory limits absent",
            pattern="CKV_K8S_12",
        ),
        SousRegle(
            type_fichier="yaml",
            outil="checkov",
            description="CPU requests absent",
            pattern="CKV_K8S_13",
        ),
    ],
)

# --------------------------------------------------------------------------
# Regle 9 — Sauvegarde
# --------------------------------------------------------------------------
REGLE_9 = GoldenRule(
    id=9,
    nom="Sauvegarde",
    description=(
        "Les donnees persistantes doivent etre sauvegardees et restaurables : "
        "backups de base de donnees configures, volumes persistants declares "
        "et artefacts de CI/CD conserves."
    ),
    severite="critique",
    sous_regles=[
        SousRegle(
            type_fichier="tf",
            outil="checkov",
            description="Backup RDS non configuré",
            pattern="CKV_AWS_28",
        ),
        SousRegle(
            type_fichier="yaml",
            outil="checkov",
            description="PersistentVolumeClaim absent",
            pattern="CKV_K8S_6",
        ),
        SousRegle(
            type_fichier="cicd",
            outil="python",
            description="Artifacts CI/CD non sauvegardés",
            pattern="ABSENT:artifacts",
        ),
    ],
)

# --------------------------------------------------------------------------
# Regle 10 — Conformite
# --------------------------------------------------------------------------
REGLE_10 = GoldenRule(
    id=10,
    nom="Conformité",
    description=(
        "Le projet doit etre juridiquement et organisationnellement "
        "identifiable : licence presente et declaree, et ressources cloud "
        "taguees pour la refacturation et la tracabilite."
    ),
    severite="warning",
    sous_regles=[
        SousRegle(
            type_fichier="license",
            outil="python",
            description="Fichier LICENSE absent",
            pattern="FICHIER_ABSENT:LICENSE,LICENCE",
        ),
        SousRegle(
            type_fichier="package.json",
            outil="python",
            description="Champ license absent",
            pattern="CLE_ABSENTE:license",
        ),
        SousRegle(
            type_fichier="yaml",
            outil="checkov",
            description="Tags absents sur les ressources",
            pattern="CKV_AWS_6",
        ),
    ],
)

# Referentiel complet, dans l'ordre des identifiants.
GOLDEN_RULES: List[GoldenRule] = [
    REGLE_1,
    REGLE_2,
    REGLE_3,
    REGLE_4,
    REGLE_5,
    REGLE_6,
    REGLE_7,
    REGLE_8,
    REGLE_9,
    REGLE_10,
]


def get_rule_by_id(rule_id: int) -> Optional[GoldenRule]:
    """Retourne la Golden Rule portant cet identifiant.

    Args:
        rule_id: identifiant de la regle, de 1 a 10.

    Returns:
        La GoldenRule correspondante, ou None si l'id est inconnu
        (cas d'un check Checkov non mappe, ou id -1).
    """
    for regle in GOLDEN_RULES:
        if regle.id == rule_id:
            return regle
    return None
