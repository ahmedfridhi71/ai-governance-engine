"""
Adaptateur LLMAnalyzer — couche Adapters.

Expose les deux modes d'analyse par LLM, fichier par fichier :

    analyser_complexe : regles 1, 4, 5 et 6 uniquement, pour un fichier
        deja couvert par Checkov ou par l'analyseur Python. Le LLM n'y
        cherche que ce que les regex ne savent pas voir.

    analyser_complet : les 10 Golden Rules, pour un fichier qu'aucun
        analyseur deterministe ne sait lire (nginx.conf, Makefile, .sql...).

Les prompts et le filtrage des reponses sont implementes une seule fois,
dans AnalyzeProject : cet adaptateur ne fait que les rendre appelables
sur un fichier isole.
"""

import logging

from ...use_cases.analyze_project import AnalyzeProject

logger = logging.getLogger(__name__)


class LLMAnalyzer:
    """Interroge le LLM sur un fichier, en mode cible ou complet."""

    def __init__(self, moteur: AnalyzeProject = None):
        """Prepare le moteur d'analyse sous-jacent.

        Args:
            moteur: instance d'AnalyzeProject a reutiliser. Recommande sur
                une analyse complete : chaque construction initialise un
                client Checkov et un client LLM.
        """
        self.moteur = moteur or AnalyzeProject()

    def analyser_complexe(self, fichier) -> list:
        """Cherche les seules violations que les regex ne detectent pas.

        Args:
            fichier: le FichierProjet a analyser.

        Returns:
            Les Violation remontees par le LLM pour les regles 1, 4, 5 et
            6, avec source="llm". Liste vide si le LLM est indisponible ou
            si sa reponse est inexploitable.
        """
        violations = self.moteur._analyser_llm_complexe(fichier)

        logger.debug(
            "LLM (regles complexes) : %d violation(s) sur %s",
            len(violations),
            fichier.chemin,
        )
        return violations

    def analyser_complet(self, fichier) -> list:
        """Cherche les violations des 10 Golden Rules.

        Args:
            fichier: le FichierProjet a analyser.

        Returns:
            Les Violation remontees par le LLM, toutes regles confondues,
            avec source="llm". Liste vide si le LLM est indisponible ou si
            sa reponse est inexploitable.
        """
        violations = self.moteur._analyser_llm_complet(fichier)

        logger.debug(
            "LLM (10 regles) : %d violation(s) sur %s",
            len(violations),
            fichier.chemin,
        )
        return violations
