"""
Use case DeduplicateViolations — supprime les doublons entre analyseurs.

Les trois analyseurs (Checkov, Python custom, LLM) travaillent en parallele
sur les memes fichiers : un meme probleme est donc souvent remonte deux ou
trois fois. On ne garde qu'une violation par probleme reel, celle issue de
l'analyseur le plus fiable.

Deux violations sont considerees identiques lorsqu'elles partagent :
    (fichier, regle_id, debut de la description du probleme)

Le numero de ligne est volontairement exclu de la cle : les analyseurs ne
s'accordent pas toujours a la ligne pres sur un meme probleme.
"""

import logging

logger = logging.getLogger(__name__)

# Nombre de caracteres de "probleme" retenus dans la cle de deduplication.
# Assez pour distinguer deux problemes, assez court pour tolerer les
# formulations divergentes en fin de phrase.
LONGUEUR_CLE_PROBLEME = 50

# Fiabilite des analyseurs, du plus sur au moins sur.
# Checkov est un outil deterministe et reconnu, l'analyse Python custom est
# deterministe mais maison, le LLM est le plus expressif mais le moins fiable.
PRIORITE_SOURCES = {
    "checkov": 3,
    "python": 2,
    "llm": 1,
}

# Source inconnue ou absente : moins prioritaire que tout le reste.
PRIORITE_INCONNUE = 0


class DeduplicateViolations:
    """Fusionne les violations identiques remontees par plusieurs analyseurs."""

    def executer(self, violations: list) -> list:
        """Supprime les doublons d'une liste de violations.

        Args:
            violations: violations brutes, toutes sources confondues.

        Returns:
            Liste dedupliquee, dans l'ordre de premiere apparition. Pour
            chaque doublon, la violation conservee est celle dont la source
            est la plus fiable.
        """
        if not violations:
            return []

        # Cle -> violation retenue jusqu'a present. Un dict conserve l'ordre
        # d'insertion : l'ordre de premiere apparition est donc preserve, meme
        # lorsqu'une violation est remplacee par une meilleure source.
        retenues = {}

        for violation in violations:
            cle = self._cle(violation)
            precedente = retenues.get(cle)

            if precedente is None:
                retenues[cle] = violation
                continue

            # Doublon : on garde la source la plus fiable. A egalite, la
            # premiere rencontree l'emporte (aucun critere pour departager).
            if self._priorite(violation) > self._priorite(precedente):
                retenues[cle] = violation

        doublons = len(violations) - len(retenues)
        if doublons:
            logger.info(
                "Deduplication : %d doublon(s) supprime(s) (%d -> %d violations)",
                doublons,
                len(violations),
                len(retenues),
            )

        return list(retenues.values())

    def _cle(self, violation) -> tuple:
        """Construit la cle d'identite d'une violation."""
        probleme = (violation.probleme or "")[:LONGUEUR_CLE_PROBLEME]
        return (violation.fichier, violation.regle_id, probleme)

    def _priorite(self, violation) -> int:
        """Renvoie le niveau de fiabilite de la source d'une violation."""
        return PRIORITE_SOURCES.get(violation.source, PRIORITE_INCONNUE)
