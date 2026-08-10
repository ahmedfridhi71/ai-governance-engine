"""
Client MongoDB — couche Infrastructure.

Persiste et relit les rapports d'analyse. Aucune logique metier ici :
le client recoit et rend des dictionnaires bruts.

Configuration (variables d'environnement) :
    MONGODB_URL : URI de connexion  (defaut "mongodb://localhost:27017")
    DB_NAME     : nom de la base    (defaut "ai_governance")

Dependance : pymongo (`pip install pymongo`). L'import est tolerant pour
que le module reste importable sans la dependance ; le client se marque
alors indisponible et toutes les operations echouent proprement.
"""

import logging
import os

try:
    from pymongo import MongoClient, DESCENDING
    from bson import ObjectId
except ImportError:  # dependance non installee
    MongoClient = None
    DESCENDING = -1
    ObjectId = None

logger = logging.getLogger(__name__)

# Nom de la collection qui stocke les rapports de conformite.
COLLECTION_RAPPORTS = "rapports"

# Nombre maximal de rapports remontes par get_rapports().
LIMITE_RAPPORTS = 50


class MongoDBClient:
    """Acces a la collection "rapports" de MongoDB."""

    def __init__(self):
        """Ouvre la connexion a MongoDB a partir des variables d'environnement.

        La connexion PyMongo est paresseuse : une URL invalide ne leve pas
        ici, mais au premier appel reseau. En cas d'echec, `disponible`
        passe a False et les methodes renvoient des valeurs neutres.
        """
        self.url = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
        self.db_name = os.environ.get("DB_NAME", "ai_governance")
        self.disponible = False
        self.client = None
        self.db = None
        self.collection = None

        if MongoClient is None:
            logger.error("pymongo n'est pas installe (pip install pymongo)")
            return

        try:
            self.client = MongoClient(self.url, serverSelectionTimeoutMS=5000)
            self.db = self.client[self.db_name]
            self.collection = self.db[COLLECTION_RAPPORTS]
            self.disponible = True
            logger.info("Client MongoDB initialise sur %s/%s", self.url, self.db_name)
        except Exception as erreur:
            logger.error("Connexion MongoDB impossible (%s) : %s", self.url, erreur)

    def sauvegarder_rapport(self, rapport_dict: dict) -> str:
        """Insere un rapport dans la collection.

        Args:
            rapport_dict: le rapport serialise en dictionnaire.

        Returns:
            L'identifiant Mongo du document insere, ou "" en cas d'echec.
        """
        if not self.disponible:
            logger.error("Sauvegarde impossible : client MongoDB indisponible")
            return ""

        try:
            resultat = self.collection.insert_one(rapport_dict)
            logger.info("Rapport sauvegarde : %s", resultat.inserted_id)
            return str(resultat.inserted_id)
        except Exception as erreur:
            logger.error("Echec de la sauvegarde du rapport : %s", erreur)
            return ""

    def get_rapports(self) -> list:
        """Retourne les 50 derniers rapports, du plus recent au plus ancien.

        Returns:
            Une liste de dictionnaires dont le champ `_id` est converti
            en chaine (serialisable en JSON), ou [] en cas d'echec.
        """
        if not self.disponible:
            logger.error("Lecture impossible : client MongoDB indisponible")
            return []

        try:
            curseur = (
                self.collection.find()
                .sort("date_analyse", DESCENDING)
                .limit(LIMITE_RAPPORTS)
            )
            rapports = []
            for document in curseur:
                # ObjectId n'est pas serialisable en JSON : on le convertit.
                document["_id"] = str(document["_id"])
                rapports.append(document)
            logger.info("%d rapport(s) relu(s)", len(rapports))
            return rapports
        except Exception as erreur:
            logger.error("Echec de la lecture des rapports : %s", erreur)
            return []

    def get_rapport_by_id(self, rapport_id: str) -> dict:
        """Retourne un rapport precis par son identifiant Mongo.

        Args:
            rapport_id: identifiant sous forme de chaine hexadecimale.

        Returns:
            Le rapport avec `_id` converti en chaine, ou None si
            l'identifiant est invalide, inconnu ou en cas d'echec.
        """
        if not self.disponible:
            logger.error("Lecture impossible : client MongoDB indisponible")
            return None

        try:
            document = self.collection.find_one({"_id": ObjectId(rapport_id)})
            if document is None:
                logger.info("Aucun rapport pour l'identifiant %s", rapport_id)
                return None
            document["_id"] = str(document["_id"])
            return document
        except Exception as erreur:
            # Couvre aussi l'ObjectId malforme (bson.errors.InvalidId).
            logger.error("Echec de la lecture du rapport %s : %s", rapport_id, erreur)
            return None
