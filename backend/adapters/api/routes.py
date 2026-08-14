"""
Routes HTTP — couche Adapters.

Expose le moteur de gouvernance en API REST. Ce module ne contient aucune
regle metier : il traduit une requete HTTP en enchainement de use cases,
puis le resultat en reponse JSON.

Routes :
    POST /analyze              lance une analyse complete d'un depot
    GET  /rapports             liste les derniers rapports
    GET  /rapports/{id}        relit un rapport precis
    GET  /health               sonde de vie du service
"""

import logging
import threading

from fastapi import APIRouter, HTTPException, status

from ...use_cases.analyze_project import AnalyzeProject
from ...use_cases.calculate_score import CalculateScore
from ...use_cases.clone_repo import CloneRepo
from ...use_cases.crawl_project import CrawlProject
from ...use_cases.deduplicate_violations import DeduplicateViolations
from ...use_cases.explain_violations import ExplainViolations
from ...use_cases.generate_report import GenerateReport
from ..repositories.rapport_repository import RapportRepository
from .schemas import AnalyzeRequest, RapportResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["gouvernance"])

# --- Instances partagees ----------------------------------------------------
#
# Les use cases sont construits une seule fois pour toute la duree de vie du
# service. Ce n'est pas qu'une economie de memoire : AnalyzeProject lance un
# sous-processus "checkov --version" a chaque construction, ExplainViolations
# relit le .env et ouvre un client Gemini, et RapportRepository ouvre un pool
# de connexions MongoDB. Les reconstruire a chaque requete gaspillerait tout
# cela, et priverait pymongo de son pool — qui est justement concu pour etre
# partage.
#
# Ce partage n'est sur que parce que les use cases sont sans etat : ils
# recoivent tout par argument et ne conservent rien entre deux appels. Toute
# future dependance mutable devra etre protegee explicitement.

_instances = {}

# Les endpoints declares en "def" tournent dans le pool de threads de FastAPI :
# deux requetes simultanees peuvent franchir le test d'existence en meme temps
# et construire deux instances, dont une serait aussitot perdue. Le verrou
# garantit une construction unique.
_verrou = threading.Lock()


def _partagee(cle: str, fabrique):
    """Retourne l'instance partagee associee a une cle, en la creant au besoin.

    Args:
        cle: identifiant de l'instance dans le registre.
        fabrique: appelable construisant l'instance si elle manque.

    Returns:
        Toujours la meme instance pour une cle donnee.
    """
    # Lecture hors verrou : une fois l'instance creee, c'est le cas courant
    # et il ne doit rien couter.
    instance = _instances.get(cle)
    if instance is not None:
        return instance

    with _verrou:
        # Re-test sous verrou : un autre thread a pu creer l'instance
        # pendant l'attente.
        if cle not in _instances:
            logger.debug("Construction de l'instance partagee : %s", cle)
            _instances[cle] = fabrique()
        return _instances[cle]


def get_clone_repo() -> CloneRepo:
    """Retourne l'instance partagee de CloneRepo."""
    return _partagee("clone_repo", CloneRepo)


def get_crawl_project() -> CrawlProject:
    """Retourne l'instance partagee de CrawlProject."""
    return _partagee("crawl_project", CrawlProject)


def get_analyze_project() -> AnalyzeProject:
    """Retourne l'instance partagee d'AnalyzeProject."""
    return _partagee("analyze_project", AnalyzeProject)


def get_deduplicate_violations() -> DeduplicateViolations:
    """Retourne l'instance partagee de DeduplicateViolations."""
    return _partagee("deduplicate_violations", DeduplicateViolations)


def get_explain_violations() -> ExplainViolations:
    """Retourne l'instance partagee d'ExplainViolations."""
    return _partagee("explain_violations", ExplainViolations)


def get_calculate_score() -> CalculateScore:
    """Retourne l'instance partagee de CalculateScore."""
    return _partagee("calculate_score", CalculateScore)


def get_generate_report() -> GenerateReport:
    """Retourne l'instance partagee de GenerateReport."""
    return _partagee("generate_report", GenerateReport)


def get_rapport_repository() -> RapportRepository:
    """Retourne l'instance partagee de RapportRepository."""
    return _partagee("rapport_repository", RapportRepository)


@router.post("/analyze", response_model=RapportResponse)
def analyser_depot(requete: AnalyzeRequest) -> RapportResponse:
    """Analyse un depot Git et retourne son rapport de conformite.

    Enchaine le pipeline complet : clonage, inventaire, analyse par les
    trois analyseurs, deduplication, enrichissement LLM, score, rapport,
    puis persistance.

    Definie en `def` et non en `async def` : le pipeline est bloquant
    (sous-processus git et checkov, appels LLM). FastAPI l'execute donc
    dans son pool de threads au lieu de figer la boucle d'evenements.

    Args:
        requete: l'URL du depot a analyser.

    Returns:
        Le rapport de conformite complet.

    Raises:
        HTTPException: 400 si le depot est inaccessible, 500 si l'analyse
            echoue pour une autre raison.
    """
    logger.info("Analyse demandee : %s", requete.url)

    # a. Cloner le depot. C'est la seule etape dont l'echec est imputable
    #    au client (URL fausse, depot prive) : elle merite un 400.
    try:
        chemin = get_clone_repo().executer(requete.url)
    except ValueError as erreur:
        logger.error("Clonage impossible : %s", erreur)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(erreur)
        ) from erreur

    try:
        # b. Inventorier les fichiers a analyser.
        fichiers = get_crawl_project().executer(chemin)
        total_fichiers = sum(len(liste) for liste in fichiers.values())

        # c. Lancer les analyseurs (Checkov, Python custom, LLM).
        violations = get_analyze_project().executer(fichiers)

        # d. Un meme probleme peut etre vu par plusieurs analyseurs.
        violations = get_deduplicate_violations().executer(violations)

        # e. Enrichir apres deduplication : enrichir des doublons
        #    couterait autant d'appels LLM inutiles.
        violations = get_explain_violations().executer(violations)

        # f. Noter la conformite.
        score, statut = get_calculate_score().executer(violations)

        # g. Assembler le rapport final.
        rapport = get_generate_report().executer(
            repo_url=requete.url,
            violations=violations,
            score=score,
            statut=statut,
            total_fichiers=total_fichiers,
            fichiers_analyses=total_fichiers,
        )
    except Exception as erreur:
        logger.exception("Analyse interrompue pour %s", requete.url)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analyse impossible : {erreur}",
        ) from erreur

    # h. Persister. Une base indisponible ne doit pas faire perdre une
    #    analyse deja payee en temps de calcul et en appels LLM : on
    #    journalise et on rend quand meme le rapport.
    identifiant = get_rapport_repository().sauvegarder(rapport)
    if identifiant:
        logger.info("Rapport %s enregistre pour %s", identifiant, requete.url)

    logger.info("Analyse terminee : %s -> %d/100 (%s)", requete.url, score, statut)
    return RapportResponse(**rapport)


@router.get("/rapports")
def lister_rapports() -> list:
    """Retourne les derniers rapports enregistres.

    Les documents sont rendus tels quels, avec leur champ `_id` : c'est
    lui qui permet ensuite d'appeler GET /rapports/{id}.

    Returns:
        La liste des rapports, du plus recent au plus ancien. Liste vide
        si la base est indisponible.
    """
    rapports = get_rapport_repository().get_rapports()
    logger.info("%d rapport(s) retourne(s)", len(rapports))
    return rapports


@router.get("/rapports/{rapport_id}")
def lire_rapport(rapport_id: str) -> dict:
    """Retourne un rapport precis.

    Args:
        rapport_id: identifiant du rapport.

    Returns:
        Le rapport demande.

    Raises:
        HTTPException: 404 si aucun rapport ne porte cet identifiant.
    """
    rapport = get_rapport_repository().get_rapport_by_id(rapport_id)

    if rapport is None:
        logger.info("Rapport introuvable : %s", rapport_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rapport introuvable : {rapport_id}",
        )

    return rapport


@router.get("/health")
def sonde_de_vie() -> dict:
    """Indique que le service repond.

    Returns:
        {"status": "ok"}
    """
    return {"status": "ok"}
