"""
Client Checkov — couche Infrastructure.

Lance l'outil Checkov en sous-processus sur un fichier ou un dossier et
normalise sa sortie JSON en une liste de dictionnaires simples.

Checkov est appele en ligne de commande (et non via son API Python) pour
isoler ses dependances et pouvoir le remplacer sans toucher au reste.

Configuration (variables d'environnement) :
    CHECKOV_TIMEOUT : delai maximal d'une analyse en secondes (defaut 30)

Le client est tolerant : si Checkov n'est pas installe, `disponible` vaut
False et les analyses retournent une liste vide au lieu d'echouer.
"""

import json
import logging
import os
import subprocess

logger = logging.getLogger(__name__)

# Delai maximal accorde a une execution de Checkov, en secondes.
CHECKOV_TIMEOUT = int(os.environ.get("CHECKOV_TIMEOUT", "30"))

# Delai court pour le simple test de presence de l'outil.
VERSION_TIMEOUT = 10


class CheckovClient:
    """Execute Checkov et renvoie ses violations sous forme normalisee."""

    def __init__(self):
        """Verifie que la commande `checkov` est disponible sur la machine."""
        self.disponible = False
        try:
            resultat = subprocess.run(
                ["checkov", "--version"],
                capture_output=True,
                text=True,
                timeout=VERSION_TIMEOUT,
            )
            self.disponible = resultat.returncode == 0
            if self.disponible:
                logger.info("Checkov disponible (version %s)", resultat.stdout.strip())
            else:
                logger.error(
                    "Checkov repond mais en erreur : %s", resultat.stderr.strip()
                )
        except FileNotFoundError:
            logger.error("Checkov n'est pas installe (pip install checkov)")
        except subprocess.TimeoutExpired:
            logger.error("Checkov n'a pas repondu au test de version")
        except Exception as erreur:
            logger.error("Verification de Checkov impossible : %s", erreur)

    def analyser_fichier(self, chemin: str) -> list:
        """Analyse un fichier unique.

        Args:
            chemin: chemin du fichier a analyser.

        Returns:
            La liste des violations trouvees, [] si Checkov est absent
            ou si l'analyse echoue.
        """
        return self._executer(["-f", chemin], chemin)

    def analyser_dossier(self, chemin: str) -> list:
        """Analyse recursivement un dossier.

        Args:
            chemin: racine du dossier a analyser.

        Returns:
            La liste des violations trouvees, [] si Checkov est absent
            ou si l'analyse echoue.
        """
        return self._executer(["-d", chemin], chemin)

    def _executer(self, cible: list, chemin: str) -> list:
        """Lance Checkov et normalise sa sortie.

        Args:
            cible: arguments designant la cible (["-f", ...] ou ["-d", ...]).
            chemin: la cible, pour les messages de log.

        Returns:
            La liste normalisee des violations.
        """
        if not self.disponible:
            logger.error("Analyse Checkov ignoree (outil indisponible) : %s", chemin)
            return []

        commande = ["checkov", *cible, "-o", "json", "--quiet", "--compact"]
        logger.info("Execution de Checkov sur %s", chemin)

        try:
            resultat = subprocess.run(
                commande,
                capture_output=True,
                text=True,
                timeout=CHECKOV_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            logger.error(
                "Checkov a depasse le delai de %ds sur %s", CHECKOV_TIMEOUT, chemin
            )
            return []
        except Exception as erreur:
            logger.error("Execution de Checkov impossible sur %s : %s", chemin, erreur)
            return []

        # Checkov sort avec le code 1 des qu'il trouve une violation :
        # la sortie JSON reste exploitable, on ne teste donc pas returncode.
        if not resultat.stdout.strip():
            logger.error("Checkov n'a rien retourne sur %s : %s", chemin, resultat.stderr.strip())
            return []

        try:
            donnees = json.loads(resultat.stdout)
        except json.JSONDecodeError as erreur:
            logger.error("Sortie Checkov illisible sur %s : %s", chemin, erreur)
            return []

        violations = self._normaliser(donnees)
        logger.info("Checkov a trouve %d violation(s) sur %s", len(violations), chemin)
        return violations

    def _normaliser(self, donnees) -> list:
        """Convertit la sortie JSON de Checkov en liste de dictionnaires.

        Checkov rend un objet lorsqu'un seul framework est concerne, et une
        liste d'objets (un par framework : kubernetes, terraform, ...)
        lorsqu'il y en a plusieurs. Les deux formes sont traitees.

        Args:
            donnees: la sortie JSON deja parsee.

        Returns:
            Une liste de dicts {check_id, check_name, file_path, resource,
            severity}.
        """
        # Toujours raisonner sur une liste de blocs.
        blocs = donnees if isinstance(donnees, list) else [donnees]

        violations = []
        for bloc in blocs:
            if not isinstance(bloc, dict):
                continue
            echecs = bloc.get("results", {}).get("failed_checks", [])
            for echec in echecs:
                violations.append({
                    "check_id": echec.get("check_id", ""),
                    "check_name": echec.get("check_name", ""),
                    "file_path": echec.get("file_path", ""),
                    "resource": echec.get("resource", ""),
                    # severity vaut null quand l'edition open source ne la
                    # fournit pas : on retombe sur une valeur neutre.
                    "severity": echec.get("severity") or "UNKNOWN",
                })

        return violations
