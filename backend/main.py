"""
Point d'entree de l'API — AI Governance Engine.

Assemble l'application FastAPI : configuration, middleware, routes.
Aucune logique metier ici, tout est delegue aux use cases via le router.

Lancement en developpement :
    uvicorn backend.main:app --reload

Documentation interactive : http://localhost:8000/docs
"""

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .adapters.api.routes import router

try:
    from dotenv import load_dotenv
except ImportError:  # dependance absente : le module reste importable
    load_dotenv = None

logger = logging.getLogger(__name__)

# Version de l'API, reprise dans la documentation et sur la route racine.
VERSION = "1.0.0"

# Prefixe de toutes les routes metier. Versionner l'URL des maintenant
# permettra d'introduire une v2 sans casser les clients existants.
PREFIXE_API = "/api/v1"

# Le .env vit a cote de ce module (backend/.env). Il est resolu depuis
# __file__ et non depuis le repertoire courant, pour que le chargement
# fonctionne quel que soit l'endroit d'ou uvicorn est lance.
CHEMIN_ENV = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")


def charger_configuration() -> None:
    """Charge les variables d'environnement depuis backend/.env.

    Doit s'executer avant toute construction de client : les clients LLM
    et MongoDB lisent l'environnement des leur initialisation.

    Sans effet si python-dotenv est absent ou si le fichier n'existe pas :
    les variables deja presentes dans l'environnement suffisent alors.
    """
    if load_dotenv is None:
        logger.warning(
            "python-dotenv n'est pas installe : .env non charge "
            "(pip install python-dotenv)"
        )
        return

    if not os.path.isfile(CHEMIN_ENV):
        logger.warning("Aucun fichier .env trouve a %s", CHEMIN_ENV)
        return

    # override=False : une variable deja definie dans l'environnement
    # (docker, CI) prime sur le fichier.
    load_dotenv(CHEMIN_ENV, override=False)
    logger.info("Configuration chargee depuis %s", CHEMIN_ENV)


# Chargement au plus tot, avant la construction de l'application.
charger_configuration()

app = FastAPI(
    title="AI Governance Engine",
    description="Analyse de conformite IT",
    version=VERSION,
)

# CORS ouvert : le frontend est servi depuis une autre origine que l'API.
#
# allow_origins=["*"] convient a un poste de developpement. En production,
# il faut y mettre la liste explicite des origines autorisees : combine a
# allow_credentials=True, le joker laisserait n'importe quel site appeler
# l'API avec les cookies de l'utilisateur.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix=PREFIXE_API)


@app.get("/")
def racine() -> dict:
    """Confirme que le service est demarre.

    Returns:
        Le nom du service, sa version et son etat.
    """
    return {
        "message": "AI Governance Engine",
        "version": VERSION,
        "status": "running",
    }
