"""
Adaptateur CheckovAnalyzer — couche Adapters.

Expose l'analyse Checkov d'un fichier sous la forme attendue par le
moteur : une liste de Violation rattachees aux Golden Rules.

L'adaptateur porte la traduction entre le vocabulaire de l'outil
(check_id, check_name) et celui du Domain (regle_id, regle_nom,
severite). Les checks qui ne correspondent a aucune Golden Rule sont
ecartes : le moteur ne remonte que ce qu'il sait expliquer.
"""

import logging

from ...domain.constants import get_rule_by_id, mapper_check_id, NON_MAPPE
from ...domain.entities import Violation
from ...infrastructure.checkov.checkov_client import CheckovClient

logger = logging.getLogger(__name__)


class CheckovAnalyzer:
    """Analyse un fichier d'infrastructure avec Checkov."""

    def __init__(self, client: CheckovClient = None):
        """Prepare le client Checkov.

        Args:
            client: client Checkov a reutiliser. Par defaut, un nouveau
                client est cree — il teste la presence de l'outil au
                demarrage, autant partager la meme instance sur toute une
                analyse plutot que de refaire ce test par fichier.
        """
        self.client = client or CheckovClient()

    def analyser(self, fichier) -> list:
        """Analyse un fichier et traduit les echecs Checkov en Violation.

        Args:
            fichier: le FichierProjet a analyser.

        Returns:
            Les Violation rattachees a une Golden Rule, avec
            source="checkov". Liste vide si Checkov est indisponible ou si
            aucun check ne concerne le referentiel.
        """
        violations = []

        # Chemin absolu : Checkov relit le fichier depuis un sous-processus
        # dont le repertoire de travail differe de celui du depot clone.
        # `chemin`, lui, est relatif et ne sert qu'a l'affichage.
        cible = fichier.chemin_absolu or fichier.chemin

        for resultat in self.client.analyser_fichier(cible):
            check_id = resultat.get("check_id", "")
            regle_id = mapper_check_id(check_id)

            # Check hors des 10 Golden Rules : hors perimetre du moteur.
            if regle_id == NON_MAPPE:
                logger.debug("Check Checkov non mappe, ignore : %s", check_id)
                continue

            violations.append(self._creer_violation(fichier, regle_id, resultat))

        logger.debug(
            "Checkov : %d violation(s) retenue(s) sur %s",
            len(violations),
            fichier.chemin,
        )
        return violations

    def _creer_violation(self, fichier, regle_id: int, resultat: dict) -> Violation:
        """Construit une Violation a partir d'un echec Checkov.

        Le nom et la severite viennent du referentiel des Golden Rules,
        jamais de Checkov : l'edition open source ne renseigne pas toujours
        `severity`, et le score doit rester coherent entre analyseurs.

        Args:
            fichier: le FichierProjet concerne.
            regle_id: la Golden Rule correspondant au check.
            resultat: l'echec normalise renvoye par le client.

        Returns:
            La Violation construite.
        """
        regle = get_rule_by_id(regle_id)
        check_id = resultat.get("check_id", "")
        libelle = resultat.get("check_name") or check_id

        return Violation(
            fichier=fichier.chemin,
            regle_id=regle_id,
            regle_nom=regle.nom if regle else f"Regle {regle_id}",
            severite=regle.severite if regle else "warning",
            probleme=f"{check_id} : {libelle}",
            source="checkov",
        )
