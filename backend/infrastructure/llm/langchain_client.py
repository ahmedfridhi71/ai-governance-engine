"""
Client LLM — couche Infrastructure.

Encapsule l'appel a Ollama via LangChain : envoi du prompt, reprise sur
erreur et extraction du JSON contenu dans la reponse (les modeles locaux
encadrent frequemment leur JSON de texte ou de balises markdown).

Configuration (variables d'environnement) :
    LLM_MODEL       : modele Ollama    (defaut "mistral")
    OLLAMA_BASE_URL : URL du serveur   (defaut "http://localhost:11434")

Dependance : langchain-ollama (ou langchain-community en repli).
L'import est tolerant pour que le module reste importable sans la
dependance ; invoquer() renvoie alors "".
"""

import json
import logging
import os
import time

try:
    # Paquet dedie, recommande aujourd'hui.
    from langchain_ollama import OllamaLLM as Ollama
except ImportError:
    try:
        # Repli sur l'implementation historique de langchain-community.
        from langchain_community.llms import Ollama
    except ImportError:  # aucune des deux dependances n'est installee
        Ollama = None

logger = logging.getLogger(__name__)

# Pause entre deux tentatives, en secondes.
DELAI_RETRY = 1


class LangChainClient:
    """Dialogue avec un modele Ollama local."""

    def __init__(self):
        """Initialise le modele a partir des variables d'environnement.

        Aucune requete reseau n'est faite ici : une instance est creee
        meme si le serveur Ollama n'est pas encore demarre.
        """
        self.model = os.environ.get("LLM_MODEL", "mistral")
        self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self.llm = None

        if Ollama is None:
            logger.error(
                "LangChain/Ollama n'est pas installe "
                "(pip install langchain-ollama)"
            )
            return

        try:
            self.llm = Ollama(model=self.model, base_url=self.base_url)
            logger.info(
                "Client LLM initialise : modele=%s url=%s", self.model, self.base_url
            )
        except Exception as erreur:
            logger.error("Initialisation du client LLM impossible : %s", erreur)

    def invoquer(self, prompt: str, retry: int = 3) -> str:
        """Envoie un prompt au LLM et retourne sa reponse brute.

        Les modeles locaux echouent parfois de facon transitoire (serveur
        occupe, modele en cours de chargement) : on retente `retry` fois
        avec une pause d'une seconde.

        Args:
            prompt: le texte envoye au modele.
            retry: nombre total de tentatives.

        Returns:
            La reponse du modele, ou "" si toutes les tentatives echouent.
        """
        if self.llm is None:
            logger.error("Appel LLM impossible : client non initialise")
            return ""

        for tentative in range(1, retry + 1):
            try:
                reponse = self.llm.invoke(prompt)
                # Selon la version, invoke() rend une chaine ou un message.
                if not isinstance(reponse, str):
                    reponse = getattr(reponse, "content", str(reponse))
                return reponse
            except Exception as erreur:
                logger.error(
                    "Echec de l'appel LLM (tentative %d/%d) : %s",
                    tentative,
                    retry,
                    erreur,
                )
                if tentative < retry:
                    time.sleep(DELAI_RETRY)

        logger.error("Appel LLM abandonne apres %d tentatives", retry)
        return ""

    def extraire_json(self, texte: str) -> dict:
        """Extrait l'objet JSON contenu dans une reponse de LLM.

        Tolere les enrobages habituels : phrase d'introduction, bloc
        markdown ```json ... ``` ou simples backticks.

        Args:
            texte: la reponse brute du modele.

        Returns:
            Le dictionnaire parse, ou {} si aucun JSON valide n'est trouve.
        """
        if not texte:
            return {}

        # 1. Retirer les balises markdown eventuelles.
        nettoye = texte.replace("```json", "").replace("```", "").strip()

        # 2. Isoler du premier "{" au dernier "}".
        debut = nettoye.find("{")
        fin = nettoye.rfind("}")
        if debut == -1 or fin == -1 or fin < debut:
            logger.error("Aucun objet JSON trouve dans la reponse du LLM")
            return {}

        bloc = nettoye[debut:fin + 1]

        # 3. Parser.
        try:
            resultat = json.loads(bloc)
        except json.JSONDecodeError as erreur:
            logger.error("JSON invalide dans la reponse du LLM : %s", erreur)
            return {}

        # json.loads peut rendre une liste ou un scalaire : on impose un dict.
        if not isinstance(resultat, dict):
            logger.error("Le JSON extrait n'est pas un objet : %s", type(resultat))
            return {}

        return resultat
