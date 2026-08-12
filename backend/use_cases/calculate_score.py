"""
Use case CalculateScore — note de conformite d'un depot analyse.

Bareme (identique a celui documente sur les Golden Rules) :
    depart          : 100 points
    violation critique : -15 points
    violation warning  :  -5 points
    plancher        : 0 (un depot ne peut pas avoir un score negatif)

Statut derive du score final :
    >= 80  : "conforme"
    50-79  : "attention"
    <  50  : "non conforme"

Le calcul attend des violations DEJA dedupliquees : un meme probleme
remonte par deux analyseurs serait sinon penalise deux fois.
"""

import logging

logger = logging.getLogger(__name__)

# Score de depart : un depot sans violation est parfait.
SCORE_DEPART = 100

# Score plancher : au-dela, inutile de continuer a soustraire.
SCORE_MINIMUM = 0

# Penalite appliquee par violation, selon sa severite.
PENALITES = {
    "critique": 15,
    "warning": 5,
}

# Seuils de passage d'un statut a l'autre.
SEUIL_CONFORME = 80
SEUIL_ATTENTION = 50


class CalculateScore:
    """Calcule le score de conformite et le statut associe."""

    def executer(self, violations: list) -> tuple:
        """Calcule le score sur 100 et le statut d'un ensemble de violations.

        Args:
            violations: violations retenues apres deduplication.

        Returns:
            Tuple (score, statut) ou score est un entier de 0 a 100 et
            statut vaut "conforme", "attention" ou "non conforme".
        """
        score = SCORE_DEPART

        for violation in violations:
            penalite = PENALITES.get(violation.severite)

            # Severite inattendue : on ne penalise pas au hasard, mais on le
            # signale car cela trahit un analyseur mal configure.
            if penalite is None:
                logger.warning(
                    "Severite inconnue '%s' sur %s (regle %s) : non penalisee",
                    violation.severite,
                    violation.fichier,
                    violation.regle_id,
                )
                continue

            score -= penalite

        score = max(SCORE_MINIMUM, score)
        statut = self._statut(score)

        logger.info(
            "Score calcule : %d/100 (%s) sur %d violation(s)",
            score,
            statut,
            len(violations),
        )

        return (score, statut)

    def _statut(self, score: int) -> str:
        """Traduit un score en statut lisible."""
        if score >= SEUIL_CONFORME:
            return "conforme"
        if score >= SEUIL_ATTENTION:
            return "attention"
        return "non conforme"
