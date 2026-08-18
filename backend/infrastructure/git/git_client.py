"""
Client Git — couche Infrastructure.

Encapsule GitPython pour cloner le depot a analyser dans un dossier
temporaire. Seul point du systeme qui parle a Git.

Configuration (variables d'environnement) :
    GIT_CLONE_TIMEOUT : delai maximal du clone en secondes (defaut 60)

Dependance : GitPython (`pip install gitpython`). L'import est tolerant
pour que le module reste importable meme si la dependance n'est pas
encore installee ; l'erreur est alors levee a l'appel de clone().
"""

import logging
import os
import shutil

try:
    import git
except ImportError:  # dependance non installee
    git = None

logger = logging.getLogger(__name__)

# Delai maximal accorde au clone, en secondes.
CLONE_TIMEOUT = int(os.environ.get("GIT_CLONE_TIMEOUT", "60"))


class GitClient:
    """Clone un depot Git distant vers un dossier local."""

    def clone(self, url: str, destination: str) -> str:
        """Clone le depot `url` dans `destination`.

        Le dossier de destination est supprime s'il existe deja, afin de
        toujours repartir d'un etat propre.

        Args:
            url: URL du depot Git (https ou ssh).
            destination: chemin local ou deposer le clone.

        Returns:
            Le chemin du dossier clone.

        Raises:
            ValueError: si GitPython est absent, si le depot est
                inaccessible ou si le clone depasse le delai imparti.
        """
        if git is None:
            message = "GitPython n'est pas installe (pip install gitpython)"
            logger.error(message)
            raise ValueError(message)

        # 1. Nettoyage d'un clone precedent.
        if os.path.exists(destination):
            logger.info("Suppression du dossier existant : %s", destination)
            try:
                shutil.rmtree(destination)
            except OSError as erreur:
                logger.error(
                    "Impossible de supprimer %s : %s", destination, erreur
                )
                raise ValueError(
                    f"Impossible de nettoyer le dossier {destination} : {erreur}"
                ) from erreur

        # 2. Clone proprement dit.
        logger.info("Clone de %s vers %s", url, destination)
        try:
            git.Repo.clone_from(
                url,
                destination,
                # Coupe le clone au-dela du delai (depot enorme, reseau bloque).
                kill_after_timeout=CLONE_TIMEOUT,
                env=self._environnement(),
            )
        except git.exc.GitCommandError as erreur:
            logger.error("Echec du clone de %s : %s", url, erreur)
            raise ValueError(
                f"Impossible de cloner le depot {url} : depot introuvable, "
                f"prive ou delai de {CLONE_TIMEOUT}s depasse"
            ) from erreur
        except Exception as erreur:  # erreur inattendue (disque plein, ...)
            logger.error("Erreur inattendue lors du clone de %s : %s", url, erreur)
            raise ValueError(
                f"Impossible de cloner le depot {url} : {erreur}"
            ) from erreur

        logger.info("Clone termine : %s", destination)
        return destination

    def _environnement(self) -> dict:
        """Construit l'environnement passe au sous-processus git.

        Deux reglages, pour deux problemes distincts :

        GIT_TERMINAL_PROMPT
            Empeche Git d'attendre indefiniment une saisie de mot de passe
            sur un depot prive : il echoue immediatement a la place.

        http.version = HTTP/1.1
            Force le protocole. Sur certains reseaux (proxy d'entreprise,
            NAT de conteneur), la negociation HTTP/2 avec GitHub casse en
            cours de transfert : "RPC failed; curl 92 HTTP/2 stream not
            closed cleanly". HTTP/1.1 est plus lent sur les gros depots,
            mais aboutit.

        La configuration est transmise par GIT_CONFIG_COUNT / _KEY_0 /
        _VALUE_0 plutot que par `git -c` : c'est le seul mecanisme qui
        traverse un environnement de sous-processus sans toucher au
        .gitconfig de la machine.

        Returns:
            L'environnement courant enrichi de ces reglages.
        """
        # Copie de l'environnement reel : le remplacer entierement priverait
        # git de PATH, HOME et des variables proxy.
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GIT_CONFIG_COUNT"] = "1"
        env["GIT_CONFIG_KEY_0"] = "http.version"
        env["GIT_CONFIG_VALUE_0"] = "HTTP/1.1"
        return env
