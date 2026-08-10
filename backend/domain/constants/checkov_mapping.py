"""
Correspondance Checkov -> Golden Rules — couche Domain.

Checkov produit ses propres identifiants de check (ex: "CKV_K8S_11").
Cette table les traduit en identifiants de Golden Rule (1 a 10), afin
que les violations remontees par Checkov soient rattachees a la meme
grille de gouvernance que celles trouvees par l'analyseur Python ou le LLM.

Les checks non references ici sont volontairement ignores : le moteur ne
remonte que ce qui correspond aux 10 Golden Rules.

Aucune dependance externe : uniquement la stdlib Python.
"""

from typing import Dict

# Prefixe (ou identifiant complet) de check Checkov -> id de Golden Rule.
CHECKOV_MAPPING: Dict[str, int] = {
    # --- Regle 1 : Secrets en clair -------------------------------------
    "CKV_SECRET": 1,        # famille complete des checks de secrets
    "CKV_AWS_41": 1,        # rotation des cles KMS

    # --- Regle 2 : Versionnement ----------------------------------------
    "CKV_K8S_14": 2,        # image sans tag de version (latest)
    "CKV_TF_1": 2,          # module Terraform sans version figee
    "CKV_DOCKER_7": 2,      # instruction FROM sans version

    # --- Regle 6 : Securite des acces ------------------------------------
    "CKV_K8S_30": 6,        # escalade de privileges autorisee
    "CKV_K8S_32": 6,        # conteneur execute en root
    "CKV_K8S_36": 6,        # capability NET_RAW non retiree
    "CKV_AWS_20": 6,        # bucket S3 accessible publiquement
    "CKV_AWS_18": 6,        # journalisation des acces S3 absente

    # --- Regle 7 : Disponibilite ------------------------------------------
    "CKV_K8S_8": 7,         # liveness probe absente
    "CKV_K8S_9": 7,         # readiness probe absente
    "CKV_K8S_20": 7,        # replicas insuffisants

    # --- Regle 8 : Limite des ressources ----------------------------------
    "CKV_K8S_11": 8,        # limite CPU absente
    "CKV_K8S_12": 8,        # limite memoire absente
    "CKV_K8S_13": 8,        # requests CPU absentes

    # --- Regle 9 : Sauvegarde ---------------------------------------------
    "CKV_AWS_28": 9,        # sauvegarde RDS non configuree
    "CKV_AWS_133": 9,       # retention des sauvegardes RDS
    "CKV_AWS_8": 9,         # sauvegarde des volumes EC2
    "CKV_K8S_6": 9,         # PersistentVolumeClaim absent

    # --- Regle 10 : Conformite --------------------------------------------
    "CKV_AWS_6": 10,        # tags absents sur les ressources S3
    "CKV_AZURE_1": 10,      # tags absents sur les ressources Azure
}

# Valeur retournee lorsqu'aucune Golden Rule ne correspond au check.
NON_MAPPE: int = -1


def mapper_check_id(check_id: str) -> int:
    """Traduit un identifiant de check Checkov en id de Golden Rule.

    La correspondance est cherchee d'abord a l'identique, puis par prefixe
    (utile pour la famille "CKV_SECRET_*"). Un prefixe n'est retenu que si
    le caractere qui le suit n'est pas un chiffre, afin que "CKV_TF_1" ne
    capture pas "CKV_TF_12". Le prefixe le plus long l'emporte.

    Args:
        check_id: identifiant remonte par Checkov (ex: "CKV_K8S_11").

    Returns:
        L'id de Golden Rule (1 a 10), ou -1 si le check n'est pas mappe.
    """
    if not check_id:
        return NON_MAPPE

    cid = check_id.strip().upper()

    # Correspondance exacte : le cas le plus frequent.
    if cid in CHECKOV_MAPPING:
        return CHECKOV_MAPPING[cid]

    # Correspondance par prefixe, du plus long au plus court.
    for prefixe in sorted(CHECKOV_MAPPING, key=len, reverse=True):
        if cid.startswith(prefixe):
            suite = cid[len(prefixe):]
            # Un chiffre juste apres le prefixe = autre numero de check.
            if not suite[0].isdigit():
                return CHECKOV_MAPPING[prefixe]

    return NON_MAPPE
