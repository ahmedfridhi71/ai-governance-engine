"""
Client LLM — couche Infrastructure.

Encapsule l'appel a Google Gemini via LangChain : envoi du prompt, reprise
sur erreur et extraction du JSON contenu dans la reponse (les modeles
encadrent frequemment leur JSON de texte ou de balises markdown).

Configuration (variables d'environnement) :
    GEMINI_API_KEY  : cle d'API Google AI Studio  (obligatoire)
    LLM_MODEL       : modele Gemini               (defaut "gemini-3.5-flash")
    LLM_TEMPERATURE : temperature du modele       (defaut 0.0)

La temperature vaut 0 par defaut : on attend du modele un JSON structure
et reproductible, pas de la creativite.

Dependance : langchain-google-genai.
L'import est tolerant pour que le module reste importable sans la
dependance ; invoquer() renvoie alors "".
"""

import json
import logging
import os
import time

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:  # dependance absente : le module reste importable
    ChatGoogleGenerativeAI = None

logger = logging.getLogger(__name__)

# Pause entre deux tentatives, en secondes.
DELAI_RETRY = 1

# Signatures d'un quota epuise dans le message d'erreur de l'API.
# Contrairement a une panne passagere, ce refus ne se resoudra pas en
# quelques secondes : le retenter ne fait que perdre du temps.
SIGNATURES_QUOTA = ("429", "RESOURCE_EXHAUSTED", "quota")

# Modele par defaut : la variante "flash" est la plus rapide et reste
# accessible avec le quota gratuit d'AI Studio.
#
# Version figee volontairement, et non l'alias "gemini-flash-latest" :
# un moteur de gouvernance doit rendre le meme verdict d'une analyse a
# l'autre, ce qu'un alias qui glisse vers un nouveau modele ne garantit pas.
# Les modeles 1.5 et 2.5 renvoient desormais 404 pour les nouveaux comptes.
MODELE_DEFAUT = "gemini-3.5-flash"


class LangChainClient:
    """Dialogue avec un modele Gemini via l'API Google AI Studio."""

    def __init__(self):
        """Initialise le modele a partir des variables d'environnement.

        Aucune requete reseau n'est faite ici : une instance est creee meme
        si la cle est invalide, l'erreur ne remontera qu'au premier appel.
        """
        self.model = os.environ.get("LLM_MODEL", MODELE_DEFAUT)
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        self.temperature = self._temperature()
        self.llm = None

        if ChatGoogleGenerativeAI is None:
            logger.error(
                "langchain-google-genai n'est pas installe "
                "(pip install langchain-google-genai)"
            )
            return

        # Sans cle, inutile de construire le client : chaque appel
        # echouerait sur une erreur d'authentification.
        if not self.api_key:
            logger.error(
                "GEMINI_API_KEY absente de l'environnement : "
                "l'analyse LLM sera ignoree"
            )
            return

        try:
            self.llm = ChatGoogleGenerativeAI(
                model=self.model,
                google_api_key=self.api_key,
                temperature=self.temperature,
            )
            logger.info(
                "Client LLM initialise : modele=%s temperature=%s",
                self.model,
                self.temperature,
            )
        except Exception as erreur:
            logger.error("Initialisation du client LLM impossible : %s", erreur)

    def invoquer(self, prompt: str, retry: int = 3) -> str:
        """Envoie un prompt au LLM et retourne sa reponse brute.

        L'API echoue parfois de facon transitoire (service occupe, modele
        en cours de chargement) : on retente `retry` fois avec une pause
        d'une seconde.

        Un quota epuise est traite a part : il ne se resoudra pas dans la
        seconde, et une analyse porte sur des centaines de fichiers. Le
        client se desactive alors definitivement, ce qui evite des
        milliers d'appels voues a l'echec. L'analyse se poursuit sans LLM,
        sur les seuls analyseurs deterministes.

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
                return self._texte(reponse)
            except Exception as erreur:
                if self._est_quota_epuise(erreur):
                    logger.warning(
                        "Quota Gemini épuisé — LLM désactivé pour cette analyse"
                    )
                    # Desactivation definitive : les appels suivants
                    # sortiront immediatement sur le test de self.llm.
                    self.llm = None
                    break

                logger.error(
                    "Echec de l'appel LLM (tentative %d/%d) : %s",
                    tentative,
                    retry,
                    erreur,
                )
                if tentative < retry:
                    time.sleep(DELAI_RETRY)
        else:
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

    def _est_quota_epuise(self, erreur: Exception) -> bool:
        """Indique si une erreur d'appel traduit un quota epuise.

        La detection se fait sur le texte du message : l'exception remontee
        par langchain-google-genai enveloppe la reponse HTTP sans exposer
        le code de statut sous forme exploitable.

        Args:
            erreur: l'exception levee par l'appel au modele.

        Returns:
            True si le message porte une signature de quota epuise.
        """
        message = str(erreur)
        return any(signature in message for signature in SIGNATURES_QUOTA)

    def _temperature(self) -> float:
        """Lit la temperature dans l'environnement, 0.0 si elle est illisible."""
        brute = os.environ.get("LLM_TEMPERATURE", "0")
        try:
            return float(brute)
        except ValueError:
            logger.warning(
                "LLM_TEMPERATURE illisible ('%s') : repli sur 0.0", brute
            )
            return 0.0

    def _texte(self, reponse) -> str:
        """Normalise la reponse de LangChain en chaine de caracteres.

        invoke() rend un AIMessage dont `content` est soit une chaine, soit
        une liste de blocs typés selon la version de langchain-core. Les
        deux formes sont ramenees a du texte.

        Args:
            reponse: la valeur rendue par llm.invoke().

        Returns:
            Le texte de la reponse, "" si elle n'en contient pas.
        """
        if isinstance(reponse, str):
            return reponse

        contenu = getattr(reponse, "content", None)

        if isinstance(contenu, str):
            return contenu

        # Liste de blocs : on ne garde que les morceaux textuels.
        if isinstance(contenu, list):
            morceaux = []
            for bloc in contenu:
                if isinstance(bloc, str):
                    morceaux.append(bloc)
                elif isinstance(bloc, dict) and "text" in bloc:
                    morceaux.append(str(bloc["text"]))
            return "".join(morceaux)

        if contenu is None:
            logger.error("Reponse LLM sans contenu exploitable : %s", type(reponse))
            return ""

        return str(contenu)
