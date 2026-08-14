"""
Use case ExplainViolations — enrichit les violations avec le LLM.

Les analyseurs produisent un constat factuel ("password en clair ligne 3").
Ce use case demande au LLM d'y ajouter les deux champs qui rendent le
rapport utile a un developpeur :

    explication : pourquoi c'est un risque, en deux phrases
    correction  : ce qu'il faut faire concretement

Il intervient apres la deduplication : enrichir des doublons couterait
autant d'appels LLM inutiles.

Le LLM n'est jamais bloquant. Si le service est indisponible ou si sa
reponse est inexploitable, la violation recoit un texte par defaut et
reste presente dans le rapport : un constat sans explication vaut mieux
qu'une violation perdue.
"""

import logging
import os

from ..infrastructure.llm.langchain_client import LangChainClient

try:
    from dotenv import load_dotenv
except ImportError:  # dependance absente : le module reste importable
    load_dotenv = None

logger = logging.getLogger(__name__)

# Emplacement du fichier .env du projet : backend/.env, resolu depuis ce
# module et non depuis le repertoire courant, pour que le chargement
# fonctionne quel que soit l'endroit d'ou le moteur est lance.
CHEMIN_ENV = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
)

# Gabarit du prompt. Les accolades du JSON attendu sont doublees :
# ce gabarit passe par str.format().
PROMPT_EXPLICATION = """
Tu es un expert en gouvernance IT.
Fichier : {fichier}
Regle violee : {regle_nom}
Probleme : {probleme}

Reponds UNIQUEMENT avec ce JSON :
{{
  "explication": "2 phrases max",
  "correction": "correction concrete"
}}
"""


class ExplainViolations:
    """Ajoute explication et correction a chaque violation, via le LLM."""

    def __init__(self):
        """Charge la configuration puis prepare le client LLM.

        L'ordre compte : le .env doit etre charge avant la construction du
        client, qui lit GEMINI_API_KEY dans l'environnement des son
        initialisation.
        """
        self._charger_env()
        self.llm = LangChainClient()

    def executer(self, violations: list, max_violations: int = 50) -> list:
        """Enrichit chaque violation d'une explication et d'une correction.

        L'enrichissement coute un appel LLM par violation. Sur un depot
        tres degrade, la note est deja au plancher bien avant la centieme
        violation : payer l'explication de toutes n'apporte rien et epuise
        le quota. Au-dela de `max_violations`, seules les premieres sont
        enrichies, les autres gardent leurs champs vides.

        Args:
            violations: violations dedupliquees a enrichir. Les objets sont
                modifies sur place.
            max_violations: nombre maximal de violations enrichies.

        Returns:
            La meme liste, complete. Les violations au-dela de la limite y
            figurent avec leurs champs explication et correction vides.
        """
        if not violations:
            return violations

        total = len(violations)
        a_traiter = violations

        if total > max_violations:
            logger.warning(
                "%d violations détectées — enrichissement limité à %d "
                "pour économiser le quota LLM",
                total,
                max_violations,
            )
            a_traiter = violations[:max_violations]

        retenues = len(a_traiter)

        # Un seul message si le LLM est absent, plutot qu'une erreur par
        # violation : le traitement continue avec les textes par defaut.
        # Seules les violations non enrichies sont concernees.
        if self.llm.llm is None:
            a_enrichir = sum(1 for v in a_traiter if not v.explication)
            if a_enrichir:
                logger.error(
                    "LLM indisponible : %d violation(s) sur %d recevront le "
                    "texte par defaut",
                    a_enrichir,
                    retenues,
                )

        for index, violation in enumerate(a_traiter, start=1):
            # Deja enrichie (reprise d'analyse, cache) : rien a refaire.
            if violation.explication:
                logger.debug(
                    "Explication %d/%d ignoree (deja renseignee)", index, retenues
                )
                continue

            logger.info("Explication %d/%d", index, retenues)
            self._enrichir(violation)

        return violations

    def _enrichir(self, violation) -> None:
        """Renseigne explication et correction sur une violation.

        Args:
            violation: la Violation a completer, modifiee sur place.
        """
        prompt = PROMPT_EXPLICATION.format(
            fichier=violation.fichier,
            regle_nom=violation.regle_nom,
            probleme=violation.probleme,
        )

        donnees = self.llm.extraire_json(self.llm.invoquer(prompt))

        explication = self._champ(donnees, "explication")
        correction = self._champ(donnees, "correction")

        if not explication or not correction:
            logger.warning(
                "Enrichissement LLM incomplet pour %s (regle %s) : "
                "repli sur le texte par defaut",
                violation.fichier,
                violation.regle_id,
            )

        violation.explication = explication or f"Violation de {violation.regle_nom}"
        violation.correction = correction or "Corriger selon bonnes pratiques"

    def _champ(self, donnees: dict, cle: str) -> str:
        """Lit un champ texte de la reponse du LLM.

        La reponse d'un modele n'est jamais tenue pour acquise : le champ
        peut manquer, etre nul ou ne pas etre une chaine.

        Args:
            donnees: le JSON extrait de la reponse.
            cle: le nom du champ attendu.

        Returns:
            La valeur nettoyee, "" si elle est absente ou inexploitable.
        """
        valeur = donnees.get(cle)
        if not isinstance(valeur, str):
            return ""
        return valeur.strip()

    def _charger_env(self) -> None:
        """Charge les variables d'environnement depuis backend/.env.

        Sans effet si python-dotenv n'est pas installe ou si le fichier
        n'existe pas : les variables deja presentes dans l'environnement
        suffisent alors, et le client LLM signalera lui-meme une cle
        manquante.
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
