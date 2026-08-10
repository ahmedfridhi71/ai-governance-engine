"""
Use case FilterFiles — decide si un fichier merite d'etre analyse.

Applique les listes noires du Domain, puis deux garde-fous de taille :
un fichier vide n'a rien a dire, un fichier de plus de 5 Mo coute trop
cher a lire et a envoyer au LLM pour ce qu'il apporte.

Configuration (variables d'environnement) :
    TAILLE_MAX_FICHIER  : taille maximale en octets   (defaut 5 Mo)
    SEUIL_AVERTISSEMENT : seuil d'alerte en octets    (defaut 1 Mo)
"""

import logging
import os

from ..domain.constants import doit_ignorer

logger = logging.getLogger(__name__)

# Un mega-octet, en octets.
UN_MO = 1024 * 1024

# Au-dela : le fichier est ecarte.
TAILLE_MAX = int(os.environ.get("TAILLE_MAX_FICHIER", str(5 * UN_MO)))

# Au-dela : le fichier est garde, mais signale comme volumineux.
SEUIL_AVERTISSEMENT = int(os.environ.get("SEUIL_AVERTISSEMENT", str(UN_MO)))


class FilterFiles:
    """Filtre les fichiers a analyser."""

    def executer(self, chemin: str, nom: str, extension: str) -> bool:
        """Indique si un fichier doit etre garde pour analyse.

        Args:
            chemin: chemin du fichier (absolu de preference).
            nom: nom du fichier seul, extension comprise.
            extension: extension avec le point (ex: ".py"), vide si absente.

        Returns:
            True s'il faut GARDER le fichier, False s'il faut l'IGNORER.
        """
        # 1. Listes noires du Domain : dossier technique, binaire, fichier genere.
        if doit_ignorer(chemin, nom, extension):
            logger.debug("Ignore (liste noire) : %s", chemin)
            return False

        # 2. Controles de taille. Si le fichier n'est pas lisible sur le disque
        #    (chemin theorique, permission refusee), on ne peut pas trancher
        #    sur la taille : on garde et la lecture decidera.
        try:
            taille = os.path.getsize(chemin)
        except OSError as erreur:
            logger.debug("Taille illisible pour %s (%s) : garde", chemin, erreur)
            return True

        if taille == 0:
            logger.debug("Ignore (fichier vide) : %s", chemin)
            return False

        if taille > TAILLE_MAX:
            logger.debug(
                "Ignore (trop volumineux : %.1f Mo) : %s", taille / UN_MO, chemin
            )
            return False

        # 3. Entre le seuil d'alerte et la taille maximale : garde, mais signale.
        if taille > SEUIL_AVERTISSEMENT:
            logger.warning("Fichier volumineux : %s (%.1fMB)", nom, taille / UN_MO)

        return True
