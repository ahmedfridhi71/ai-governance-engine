"""
Use case GenerateReport — assemble le rapport final d'une analyse.

Derniere etape du pipeline : les violations sont deja dedupliquees et le
score deja calcule. Ce use case se contente de tout rassembler dans une
entite Rapport, d'y ajouter la synthese chiffree et l'horodatage, puis de
la convertir en dictionnaire pret a etre renvoye par l'API et persiste
en base.

Synthese produite :
    critiques : nombre de violations de severite "critique"
    warnings  : nombre de violations de severite "warning"
    conformes : nombre de Golden Rules sans aucune violation
"""

import logging
from dataclasses import asdict
from datetime import datetime

from ..domain.constants.golden_rules import GOLDEN_RULES
from ..domain.entities.rapport import Rapport

logger = logging.getLogger(__name__)

# Nombre total de Golden Rules du referentiel (10).
# Lu depuis le referentiel plutot qu'ecrit en dur : si une regle est
# ajoutee, la synthese reste juste.
TOTAL_REGLES = len(GOLDEN_RULES)

# Identifiants de regle valides. Une violation portant un id hors de cette
# plage (ex: -1 pour un check Checkov non mappe) ne doit pas fausser le
# compte des regles respectees.
IDS_REGLES_VALIDES = {regle.id for regle in GOLDEN_RULES}


class GenerateReport:
    """Construit le rapport de conformite final."""

    def executer(
        self,
        repo_url: str,
        violations: list,
        score: int,
        statut: str,
        total_fichiers: int,
        fichiers_analyses: int,
    ) -> dict:
        """Assemble le rapport final et le renvoie sous forme de dictionnaire.

        Args:
            repo_url: URL du depot analyse.
            violations: violations retenues, apres deduplication.
            score: score de conformite sur 100.
            statut: statut derive du score ("conforme", "attention", ...).
            total_fichiers: nombre de fichiers trouves dans le depot.
            fichiers_analyses: nombre de fichiers reellement analyses.

        Returns:
            Le Rapport converti en dict (violations comprises), pret a
            etre serialise en JSON.
        """
        rapport = Rapport(
            repo_url=repo_url,
            score=score,
            statut=statut,
            violations=list(violations),
            total_fichiers=total_fichiers,
            fichiers_analyses=fichiers_analyses,
            date_analyse=datetime.now().isoformat(),
            resume=self._resume(violations),
        )

        logger.info(
            "Rapport genere pour %s : %d/100 (%s), %d violation(s)",
            repo_url,
            score,
            statut,
            len(rapport.violations),
        )

        # asdict() descend recursivement dans les Violation : le dict
        # renvoye ne contient plus aucune dataclass.
        return asdict(rapport)

    def _resume(self, violations: list) -> dict:
        """Compte les violations par severite et les regles respectees."""
        critiques = sum(1 for v in violations if v.severite == "critique")
        warnings = sum(1 for v in violations if v.severite == "warning")

        # Une regle est "conforme" si aucune violation ne la cite.
        regles_violees = {
            v.regle_id for v in violations if v.regle_id in IDS_REGLES_VALIDES
        }

        return {
            "critiques": critiques,
            "warnings": warnings,
            "conformes": TOTAL_REGLES - len(regles_violees),
        }
