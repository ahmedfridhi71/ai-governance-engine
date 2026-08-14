"""
Adaptateur PythonAnalyzer — couche Adapters.

Expose l'analyseur deterministe "maison" (regex et parsing) fichier par
fichier, la ou AnalyzeProject raisonne sur un inventaire complet.

Les regles sont implementees une seule fois, dans AnalyzeProject : cet
adaptateur ne fait que les rendre appelables sur un fichier isole, pour
les tests unitaires et pour un futur decoupage du pipeline.
"""

import logging

from ...use_cases.analyze_project import AnalyzeProject

logger = logging.getLogger(__name__)


class PythonAnalyzer:
    """Applique les regles deterministes a un fichier."""

    def __init__(self, moteur: AnalyzeProject = None):
        """Prepare le moteur d'analyse sous-jacent.

        Args:
            moteur: instance d'AnalyzeProject a reutiliser. Fortement
                recommande : construire un AnalyzeProject initialise un
                client Checkov (sous-processus) et un client LLM, alors
                que l'analyse Python n'a besoin ni de l'un ni de l'autre.
        """
        self.moteur = moteur or AnalyzeProject()

    def analyser(self, fichier) -> list:
        """Applique les regles deterministes correspondant au fichier.

        Les regles retenues dependent du nom et de l'extension : versions
        figees, secrets en clair, docstrings, logging, gestion d'erreurs,
        artefacts de pipeline, licence.

        Args:
            fichier: le FichierProjet a analyser.

        Returns:
            Les Violation detectees, avec source="python". Liste vide si
            aucune regle ne s'applique au fichier.
        """
        violations = self.moteur._analyser_python(fichier)

        logger.debug(
            "Analyse Python : %d violation(s) sur %s",
            len(violations),
            fichier.chemin,
        )
        return violations
