"""
Use case CrawlProject — parcourt le depot clone et construit l'inventaire
des fichiers a analyser, classes par categorie.

Sortie : un dictionnaire de trois listes de FichierProjet, qui determine
quels analyseurs seront lances ensuite :
    "devops" -> Checkov + LLM
    "code"   -> analyseur Python custom + LLM
    "autre"  -> LLM uniquement

Trois pieges sont traites explicitement :
  - les liens symboliques (boucles infinies, sortie du depot) sont ignores ;
  - les fichiers non-UTF-8 sont relus en latin-1 ;
  - les binaires deguises en texte (octets nuls) sont ecartes apres lecture.
"""

import logging
import os

from ..domain.constants import DOSSIERS_IGNORES, detecter_type
from ..domain.entities import FichierProjet
from .filter_files import FilterFiles

logger = logging.getLogger(__name__)


class CrawlProject:
    """Inventorie les fichiers d'un projet et les classe par categorie."""

    def __init__(self):
        """Prepare le filtre applique a chaque fichier rencontre."""
        self.filtre = FilterFiles()

    def executer(self, chemin_projet: str) -> dict:
        """Parcourt le projet et retourne les fichiers classes par type.

        Args:
            chemin_projet: racine du projet clone.

        Returns:
            Un dict {"devops": [...], "code": [...], "autre": [...]} dont
            les valeurs sont des listes de FichierProjet.
        """
        resultat = {"devops": [], "code": [], "autre": []}

        for dossier, sous_dossiers, fichiers in os.walk(chemin_projet):
            # Elague l'arborescence AVANT d'y descendre : os.walk ne visitera
            # pas .git, node_modules, .venv... ni les dossiers symboliques.
            sous_dossiers[:] = [
                sd for sd in sous_dossiers
                if sd not in DOSSIERS_IGNORES
                and not os.path.islink(os.path.join(dossier, sd))
            ]

            for nom in fichiers:
                chemin = os.path.abspath(os.path.join(dossier, nom))

                # Un lien symbolique pointe ailleurs : deja analyse, ou hors
                # du depot. Dans les deux cas on ne le suit pas.
                if os.path.islink(chemin):
                    logger.debug("Ignore (lien symbolique) : %s", chemin)
                    continue

                # Extension en minuscules : toutes les tables du Domain le sont.
                extension = os.path.splitext(nom)[1].lower()

                # Correction 1 — fichiers .env.local .env.production etc.
                # os.path.splitext(".env.local") = (".env", ".local")
                # on veut que tous les fichiers commençant par .env
                # soient traités comme .env
                if nom.startswith('.env'):
                    extension = '.env'

                # Correction 2 — fichiers cachés sans extension
                # os.path.splitext(".editorconfig") = (".editorconfig", "")
                # on veut utiliser le nom entier comme extension
                elif not extension and nom.startswith('.'):
                    extension = nom

                if not self.filtre.executer(chemin, nom, extension):
                    continue

                contenu = self._lire(chemin)
                if contenu is None:
                    continue

                try:
                    taille = os.path.getsize(chemin)
                except OSError:
                    taille = len(contenu.encode("utf-8", errors="ignore"))

                type_fichier = detecter_type(nom, extension, contenu)

                # Deux chemins, deux usages :
                #   chemin         -> affichage dans le rapport, relatif a
                #                     la racine du depot.
                #   chemin_absolu  -> relecture du fichier sur le disque,
                #                     notamment par Checkov, qui tourne en
                #                     sous-processus depuis un autre
                #                     repertoire de travail.
                resultat[type_fichier].append(
                    FichierProjet(
                        chemin=os.path.relpath(chemin, chemin_projet),
                        nom=nom,
                        type_fichier=type_fichier,
                        contenu=contenu,
                        taille=taille,
                        chemin_absolu=chemin,
                    )
                )

        logger.info(
            "Crawl termine : %d devops, %d code, %d autre",
            len(resultat["devops"]),
            len(resultat["code"]),
            len(resultat["autre"]),
        )
        return resultat

    def _lire(self, chemin: str) -> str:
        """Lit un fichier texte, avec repli d'encodage.

        UTF-8 d'abord, latin-1 ensuite (qui accepte n'importe quel octet).
        Comme latin-1 ne leve jamais d'erreur, un binaire renomme en .txt
        passerait au travers : on le detecte a la presence d'octets nuls.

        Args:
            chemin: chemin absolu du fichier.

        Returns:
            Le contenu textuel, ou None si le fichier doit etre ecarte.
        """
        contenu = None
        try:
            with open(chemin, "r", encoding="utf-8") as flux:
                contenu = flux.read()
        except UnicodeDecodeError:
            # Encodage historique (fichiers Windows/Latin) : seconde tentative.
            try:
                with open(chemin, "r", encoding="latin-1") as flux:
                    contenu = flux.read()
                logger.debug("Relu en latin-1 : %s", chemin)
            except (UnicodeDecodeError, OSError) as erreur:
                logger.debug("Ignore (illisible) : %s (%s)", chemin, erreur)
                return None
        except OSError as erreur:
            logger.debug("Ignore (lecture impossible) : %s (%s)", chemin, erreur)
            return None

        # Binaire deguise en texte : un fichier source ne contient jamais
        # d'octet nul.
        if "\x00" in contenu:
            logger.debug("Ignore (binaire deguise en texte) : %s", chemin)
            return None

        return contenu
