"""
Repository RapportRepository — couche Adapters.

Frontiere entre le moteur et la persistance : les use cases manipulent
des rapports, pas des documents MongoDB. Toute la connaissance du stockage
reste dans MongoDBClient, cote Infrastructure.

Le repository ne leve jamais : si la base est indisponible, la sauvegarde
rend "" et les lectures rendent une liste vide ou None. Une analyse reussie
ne doit pas etre perdue parce que MongoDB est arrete — le rapport est
retourne au client meme s'il n'a pas pu etre persiste.
"""

import logging

from ...infrastructure.database.mongodb_client import MongoDBClient

logger = logging.getLogger(__name__)


class RapportRepository:
    """Persiste et relit les rapports de conformite."""

    def __init__(self, client: MongoDBClient = None):
        """Prepare l'acces a la base.

        Args:
            client: client MongoDB a reutiliser. Par defaut, un nouveau
                client est cree.
        """
        self.client = client or MongoDBClient()

    def sauvegarder(self, rapport_dict: dict) -> str:
        """Enregistre un rapport.

        Args:
            rapport_dict: le rapport serialise, tel que produit par
                GenerateReport.

        Returns:
            L'identifiant du rapport enregistre sous forme de chaine, ""
            si la base est indisponible ou si l'insertion echoue.
        """
        # Copie defensive : pymongo ajoute "_id" au dictionnaire qu'il
        # recoit, et l'appelant s'en sert ensuite pour construire sa
        # reponse HTTP — un ObjectId n'y serait pas serialisable.
        identifiant = self.client.sauvegarder_rapport(dict(rapport_dict))

        if not identifiant:
            logger.warning(
                "Rapport non persiste pour %s", rapport_dict.get("repo_url", "?")
            )

        return identifiant

    def get_rapports(self) -> list:
        """Retourne les 50 derniers rapports, du plus recent au plus ancien.

        Le tri se fait sur `date_analyse` et la limite est fixee par
        MongoDBClient : le repository n'a pas a connaitre ces details de
        stockage.

        Returns:
            Une liste de rapports serialisables en JSON, leur `_id`
            converti en chaine. [] si la base est indisponible.
        """
        return self.client.get_rapports()

    def get_rapport_by_id(self, rapport_id: str) -> dict:
        """Retourne un rapport precis.

        Args:
            rapport_id: identifiant du rapport.

        Returns:
            Le rapport, son `_id` converti en chaine. None s'il est
            introuvable, si l'identifiant est malforme ou si la base est
            indisponible.
        """
        return self.client.get_rapport_by_id(rapport_id)
