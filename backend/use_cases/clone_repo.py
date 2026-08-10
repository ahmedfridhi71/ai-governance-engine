"""
Use Case CloneRepo — couche Use Cases.

Clone un depot Git distant vers un dossier local temporaire.
Utilise GitClient de la couche Infrastructure.
"""

import hashlib
import logging

from backend.infrastructure.git.git_client import GitClient

logger = logging.getLogger(__name__)


class CloneRepo:
    """Clone un depot Git et retourne le chemin local."""

    def executer(self, url: str) -> str:
        """
        Clone le depot Git vers /tmp/governance_{hash}.

        Args:
            url: URL du depot Git a cloner.

        Returns:
            Chemin absolu du dossier clone.

        Raises:
            ValueError: Si l'URL est vide ou le clone echoue.
        """
        if not url or not url.strip():
            raise ValueError("URL du depot manquante")

        # Destination deterministe — meme URL = meme dossier
        empreinte = hashlib.sha256(url.encode()).hexdigest()[:16]
        destination = f"/tmp/governance_{empreinte}"

        logger.info("Clonage de %s vers %s", url, destination)

        try:
            GitClient().clone(url, destination)
            logger.info("Clone reussi : %s", destination)
            return destination

        except Exception as e:
            raise ValueError(
                f"Impossible de cloner le depot {url} : {e}"
            ) from e
