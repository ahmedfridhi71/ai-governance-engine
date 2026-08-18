"""
Use case ExplainViolations — enrichit les violations avec le LLM.

Les analyseurs produisent un constat factuel ("password en clair ligne 3").
Ce use case demande au LLM d'y ajouter les deux champs qui rendent le
rapport utile a un developpeur :

    explication : pourquoi c'est un risque, en deux phrases
    correction  : ce qu'il faut faire concretement

Il intervient apres la deduplication : enrichir des doublons couterait
autant d'appels LLM inutiles.

L'enrichissement se fait PAR REGLE, pas par violation. Les cinquante
"dependance sans version figee" d'un depot appellent la meme explication
et la meme correction : les demander cinquante fois epuiserait le quota
sans rien apporter. Une analyse coute donc au plus dix appels, un par
Golden Rule, quel que soit le nombre de violations.

Le texte produit vaut pour toute la regle et ne cite aucun fichier
precis : le detail par fichier reste porte par le champ `probleme` de
chaque violation.

Le LLM n'est jamais bloquant. Si le service est indisponible ou si sa
reponse est inexploitable, les violations du groupe recoivent un texte
par defaut et restent presentes dans le rapport : un constat sans
explication vaut mieux qu'une violation perdue.
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

# Nombre maximal d'appels LLM par analyse. Le referentiel compte dix
# Golden Rules : au-dela, c'est qu'un analyseur remonte des identifiants
# inattendus.
MAX_APPELS = 10

# Nombre d'exemples de fichiers cites au LLM pour situer le contexte.
EXEMPLES_FICHIERS = 3

# Ordre de traitement des groupes : les regles critiques d'abord. Si le
# quota s'epuise en cours de route, ce sont les violations les plus graves
# qui auront ete expliquees, pas celles arrivees en tete par hasard.
ORDRE_SEVERITE = {"critique": 0, "warning": 1}

# Severite inattendue : traitee en dernier, apres tout ce qui est connu.
SEVERITE_INCONNUE = 2

# Gabarit du prompt. Les accolades du JSON attendu sont doublees :
# ce gabarit passe par str.format().
#
# Le prompt demande explicitement un texte valable pour tous les fichiers
# concernes : la reponse sera recopiee sur chaque violation du groupe, elle
# ne doit donc pas s'appuyer sur un fichier en particulier.
PROMPT_EXPLICATION = """
Tu es un expert en gouvernance IT.
Regle violee : {regle_nom}
Probleme constate : {probleme}
Nombre de fichiers concernes : {nombre}
Exemples de fichiers : {fichiers}

Ton explication et ta correction doivent valoir pour TOUS les fichiers
concernes : ne cite aucun fichier en particulier.

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

    def executer(self, violations: list, max_appels: int = MAX_APPELS) -> list:
        """Enrichit toutes les violations, a raison d'un appel LLM par regle.

        Les violations sont regroupees par `regle_id` : un seul appel par
        groupe, dont la reponse est recopiee sur chaque violation. Un depot
        a 849 violations reparties sur dix regles coute donc dix appels, la
        ou l'enrichissement violation par violation en coutait 849 et
        epuisait le quota des la cinquantieme.

        Args:
            violations: violations dedupliquees a enrichir. Les objets sont
                modifies sur place.
            max_appels: nombre maximal d'appels LLM, donc de regles
                enrichies.

        Returns:
            La meme liste, complete et enrichie.
        """
        if not violations:
            return violations

        # Une violation deja renseignee (reprise d'analyse, cache) ne
        # declenche aucun appel et n'entre dans aucun groupe.
        a_enrichir = [v for v in violations if not v.explication]
        if not a_enrichir:
            logger.debug("Toutes les violations sont deja enrichies")
            return violations

        groupes = self._grouper(a_enrichir)
        regles = self._retenir(groupes, max_appels)

        # Un seul message si le LLM est absent, plutot qu'une erreur par
        # groupe : le traitement continue avec les textes par defaut.
        if self.llm.llm is None:
            logger.error(
                "LLM indisponible : %d violation(s) recevront le texte "
                "par defaut",
                len(a_enrichir),
            )

        for index, regle_id in enumerate(regles, start=1):
            groupe = groupes[regle_id]
            logger.info(
                "Explication %d/%d — regle %s (%d violation(s))",
                index,
                len(regles),
                regle_id,
                len(groupe),
            )
            self._enrichir_groupe(groupe)

        logger.info(
            "Enrichissement termine : %d violation(s) couvertes en %d appel(s)",
            sum(len(groupes[r]) for r in regles),
            len(regles),
        )
        return violations

    def _grouper(self, violations: list) -> dict:
        """Regroupe les violations par identifiant de Golden Rule.

        Args:
            violations: les violations a enrichir.

        Returns:
            Un dict {regle_id: [violations]}, dans l'ordre de premiere
            apparition.
        """
        groupes = {}
        for violation in violations:
            groupes.setdefault(violation.regle_id, []).append(violation)
        return groupes

    def _retenir(self, groupes: dict, max_appels: int) -> list:
        """Ordonne les regles a enrichir et applique le budget d'appels.

        Les groupes critiques passent avant les warnings, et a severite
        egale les plus nombreux d'abord. Cet ordre n'a rien de cosmetique :
        si le quota LLM s'epuise en cours d'analyse, les violations restees
        sans explication seront les moins graves.

        Le referentiel ne comptant que dix regles, la troncature n'arrive
        que si un analyseur remonte des identifiants inattendus.

        Args:
            groupes: les groupes de violations, par regle.
            max_appels: budget d'appels LLM.

        Returns:
            Les identifiants de regle a traiter, dans l'ordre de traitement.
        """
        def cle_de_tri(regle_id):
            groupe = groupes[regle_id]
            severite = groupe[0].severite
            # Effectif negatif : le plus grand groupe passe en premier a
            # severite egale.
            return (
                ORDRE_SEVERITE.get(severite, SEVERITE_INCONNUE),
                -len(groupe),
            )

        ordre = sorted(groupes, key=cle_de_tri)

        if len(ordre) <= max_appels:
            return ordre

        logger.warning(
            "%d regles violees pour %d appel(s) LLM autorise(s) : "
            "les regles les moins graves ne seront pas expliquees",
            len(ordre),
            max_appels,
        )
        return ordre[:max_appels]

    def _enrichir_groupe(self, groupe: list) -> None:
        """Interroge le LLM une fois et applique sa reponse a tout le groupe.

        Args:
            groupe: violations partageant la meme Golden Rule, modifiees
                sur place.
        """
        # Le premier element sert de specimen : meme regle, donc meme
        # nature de probleme pour tout le groupe.
        exemple = groupe[0]
        fichiers = [v.fichier for v in groupe[:EXEMPLES_FICHIERS]]

        prompt = PROMPT_EXPLICATION.format(
            regle_nom=exemple.regle_nom,
            probleme=exemple.probleme,
            nombre=len(groupe),
            fichiers=", ".join(fichiers),
        )

        donnees = self.llm.extraire_json(self.llm.invoquer(prompt))

        explication = self._champ(donnees, "explication")
        correction = self._champ(donnees, "correction")

        if not explication or not correction:
            logger.warning(
                "Enrichissement LLM incomplet pour la regle %s "
                "(%d violation(s)) : repli sur le texte par defaut",
                exemple.regle_id,
                len(groupe),
            )

        explication = explication or f"Violation de {exemple.regle_nom}"
        correction = correction or "Corriger selon bonnes pratiques"

        for violation in groupe:
            violation.explication = explication
            violation.correction = correction

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
