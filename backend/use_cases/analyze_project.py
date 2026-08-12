"""
Use case AnalyzeProject — coeur de l'analyse de conformite.

Orchestre les trois analyseurs selon la categorie de chaque fichier :

    "devops" : Checkov (regles d'infrastructure) + LLM cible
    "code"   : analyseur Python custom (regex deterministes) + LLM cible
    "autre"  : LLM seul, sur les 10 Golden Rules

Les violations produites ne sont ni dedupliquees ni scorees ici : c'est le
role de DeduplicateViolations puis CalculateScore, en aval du pipeline.

Deux ecarts avec le modele de donnees sont geres localement :
  - FichierProjet ne porte pas d'extension : elle est deduite du nom, avec
    la meme regle que le Crawler pour la famille ".env*" ;
  - le Crawler ne produit que "devops"/"code"/"autre" : un pipeline CI/CD
    est reconnu a son nom ou a son contenu, pas a un type "cicd".
"""

import json
import logging
import os
import re

from ..domain.constants import get_rule_by_id, mapper_check_id, NON_MAPPE
from ..domain.entities import Violation
from ..infrastructure.checkov.checkov_client import CheckovClient
from ..infrastructure.llm.langchain_client import LangChainClient

logger = logging.getLogger(__name__)

# --- Reglages de l'appel LLM ------------------------------------------------

# Nombre de caracteres envoyes au LLM par appel.
FENETRE_LLM = 2000

# Au-dela de cette taille, le fichier est decoupe en plusieurs morceaux
# au lieu d'etre tronque a la premiere fenetre.
SEUIL_DECOUPAGE = 1024 * 1024

# Garde-fou : un fichier de 5 Mo donnerait 2500 morceaux, donc 2500 appels
# LLM. On plafonne le nombre de morceaux analyses par fichier.
MAX_MORCEAUX = 20

# --- Regex de l'analyseur Python custom -------------------------------------
# Toutes en re.MULTILINE : les patterns raisonnent ligne par ligne.

# Regle 2 — dependance sans version figee (ligne ne contenant qu'un nom).
RE_DEP_SANS_VERSION = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*\s*$", re.MULTILINE)

# Regle 1 — secret assigne en clair dans du code Python.
RE_SECRET_PY = re.compile(
    r'(?i)(password|passwd|pwd|secret|api_key|token)\s*=\s*["\'][^"\']{3,}["\']',
    re.MULTILINE,
)

# Regle 3 — fonction dont la premiere ligne de corps n'est pas une docstring.
RE_FONCTION_SANS_DOCSTRING = re.compile(
    r'def \w+\([^)]*\):\s*\n\s+[^"\s#]', re.MULTILINE
)

# Regle 1 — secret dans un fichier .env (valeur non quotee).
RE_SECRET_ENV = re.compile(
    r"(?i)(password|api_key|secret|token)\s*=\s*\S+", re.MULTILINE
)

# Regle 6 — mode debug actif.
RE_DEBUG_ACTIF = re.compile(r"(?i)DEBUG\s*=\s*(true|1|yes)", re.MULTILINE)

# Regle 6 — hotes autorises non restreints.
RE_HOTES_OUVERTS = re.compile(r"(?i)ALLOWED_HOSTS\s*=\s*\*", re.MULTILINE)

# --- Autres seuils ----------------------------------------------------------

# Regle 3 — en dessous, le README est considere comme vide.
TAILLE_README_MINIMALE = 100

# Regle 4 — bibliotheques de logging reconnues cote JavaScript/TypeScript.
LOGGERS_JS = ("winston", "morgan", "pino", "bunyan")

# Versions non figees rencontrees dans un package.json.
VERSIONS_FLOTTANTES = ("*", "latest")

# Sections de dependances d'un package.json.
SECTIONS_DEPENDANCES = ("dependencies", "devDependencies", "peerDependencies")

# --- Prompts LLM ------------------------------------------------------------
# Les accolades du JSON attendu sont doublees : ces gabarits passent par
# str.format().

SCHEMA_REPONSE = """
  Retourne UNIQUEMENT ce JSON :
  {{
    "violations": [
      {{
        "regle_id": int,
        "regle_nom": str,
        "severite": "critique" ou "warning",
        "probleme": str
      }}
    ]
  }}
"""

PROMPT_COMPLEXE = (
    """
  Tu es expert en securite IT.
  Fichier : {nom}
  Contenu (2000 chars max) :
  {contenu}

  Cherche UNIQUEMENT ces violations complexes :
  - Regle 1 : secrets noms non standards ou base64
  - Regle 4 : logging mal configure
  - Regle 5 : except vide, bare except,
    pas de retry sur appels reseau
  - Regle 6 : endpoints sans auth,
    SQL avec concatenation strings
"""
    + SCHEMA_REPONSE
)

PROMPT_COMPLET = (
    """
  Tu es expert en securite IT.
  Fichier : {nom}
  Contenu (2000 chars max) :
  {contenu}

  Cherche les violations des 10 Golden Rules :
  - Regle 1 : secrets en clair (mots de passe, cles d'API, tokens)
  - Regle 2 : versionnement absent (dependance ou image sans version figee)
  - Regle 3 : documentation absente ou vide
  - Regle 4 : logs non configures
  - Regle 5 : erreurs non gerees (except vide, pas de retry)
  - Regle 6 : securite des acces (auth absente, droits trop larges, SQL concatene)
  - Regle 7 : disponibilite (aucun health check, pas de redondance)
  - Regle 8 : limites de ressources absentes (CPU, memoire)
  - Regle 9 : sauvegarde absente (donnees ou artefacts non conserves)
  - Regle 10 : conformite (licence absente, tags absents)
"""
    + SCHEMA_REPONSE
)

# Regles que le LLM est autorise a remonter sur un fichier deja couvert
# par Checkov ou par l'analyseur Python : les regles "complexes", que les
# regex ne savent pas voir.
REGLES_COMPLEXES = (1, 4, 5, 6)

# Regles que le LLM peut remonter sur un fichier qu'aucun autre analyseur
# ne couvre : tout le referentiel.
REGLES_TOUTES = tuple(range(1, 11))


class AnalyzeProject:
    """Lance les analyseurs adaptes a chaque categorie de fichier."""

    def __init__(self):
        """Prepare les clients Checkov et LLM, partages par toute l'analyse.

        Les deux clients sont instancies une seule fois : CheckovClient
        teste la presence de l'outil au demarrage, et le recreer a chaque
        fichier relancerait ce test inutilement.
        """
        self.checkov = CheckovClient()
        self.llm = LangChainClient()

    def executer(self, fichiers: dict) -> list:
        """Analyse tous les fichiers inventories et retourne les violations.

        Args:
            fichiers: inventaire produit par CrawlProject, sous la forme
                {"devops": [...], "code": [...], "autre": [...]}.

        Returns:
            La liste brute des Violation trouvees, toutes sources
            confondues. Elle contient des doublons : la deduplication est
            faite ensuite par DeduplicateViolations.
        """
        violations = []

        # 1. Fichiers d'infrastructure : Checkov, puis LLM sur les regles
        #    complexes qu'un scanner statique ne voit pas.
        for fp in fichiers.get("devops", []):
            violations.extend(self._analyser_checkov(fp))
            # Les pipelines CI/CD relevent aussi d'une regle deterministe
            # (regle 9), portee par l'analyseur Python.
            violations.extend(self._analyser_python(fp))
            violations.extend(self._analyser_llm_complexe(fp))

        # 2. Code applicatif : regex deterministes, puis LLM cible.
        for fp in fichiers.get("code", []):
            violations.extend(self._analyser_python(fp))
            violations.extend(self._analyser_llm_complexe(fp))

        # 3. Reste : aucun analyseur deterministe ne sait le lire, le LLM
        #    passe donc sur les 10 regles.
        for fp in fichiers.get("autre", []):
            violations.extend(self._analyser_llm_complet(fp))

        logger.info("Analyse terminee : %d violation(s) brute(s)", len(violations))
        return violations

    # --- Analyseur Checkov --------------------------------------------------

    def _analyser_checkov(self, fp) -> list:
        """Lance Checkov sur un fichier d'infrastructure.

        Args:
            fp: le FichierProjet a analyser.

        Returns:
            Les violations rattachees a une Golden Rule. Les checks Checkov
            hors referentiel sont ignores.
        """
        violations = []

        for resultat in self.checkov.analyser_fichier(fp.chemin):
            check_id = resultat.get("check_id", "")
            regle_id = mapper_check_id(check_id)

            # Check hors des 10 Golden Rules : hors perimetre du moteur.
            if regle_id == NON_MAPPE:
                logger.debug("Check Checkov non mappe, ignore : %s", check_id)
                continue

            libelle = resultat.get("check_name") or check_id
            violations.append(
                self._creer_violation(
                    fp,
                    regle_id,
                    f"{check_id} : {libelle}",
                    source="checkov",
                )
            )

        return violations

    # --- Analyseur Python custom --------------------------------------------

    def _analyser_python(self, fp) -> list:
        """Applique les regles deterministes correspondant au fichier.

        Args:
            fp: le FichierProjet a analyser.

        Returns:
            Les violations detectees par regex ou par parsing.
        """
        contenu = fp.contenu or ""
        extension = self._extension(fp)
        violations = []

        # --- requirements.txt : dependances sans version figee -------------
        if fp.nom == "requirements.txt":
            for correspondance in RE_DEP_SANS_VERSION.finditer(contenu):
                paquet = correspondance.group().strip()
                violations.append(
                    self._creer_violation(
                        fp,
                        2,
                        f"dependance sans version figee : {paquet}",
                        ligne=self._ligne(contenu, correspondance.start()),
                    )
                )

        # --- package.json : versions flottantes et licence -----------------
        if fp.nom == "package.json":
            violations.extend(self._analyser_package_json(fp, contenu))

        # --- README : documentation trop courte ----------------------------
        if fp.nom in ("README.md", "README.rst"):
            if len(contenu.strip()) < TAILLE_README_MINIMALE:
                violations.append(
                    self._creer_violation(
                        fp,
                        3,
                        f"documentation quasi vide "
                        f"({len(contenu.strip())} caracteres)",
                    )
                )

        # --- Python --------------------------------------------------------
        if extension == ".py":
            for correspondance in RE_SECRET_PY.finditer(contenu):
                violations.append(
                    self._creer_violation(
                        fp,
                        1,
                        f"secret en clair : {self._extrait(correspondance.group())}",
                        ligne=self._ligne(contenu, correspondance.start()),
                    )
                )

            for correspondance in RE_FONCTION_SANS_DOCSTRING.finditer(contenu):
                # La premiere ligne de la correspondance porte le "def".
                declaration = correspondance.group().splitlines()[0].strip()
                violations.append(
                    self._creer_violation(
                        fp,
                        3,
                        f"fonction sans docstring : {declaration}",
                        ligne=self._ligne(contenu, correspondance.start()),
                    )
                )

            if "import logging" not in contenu:
                violations.append(
                    self._creer_violation(fp, 4, "module logging non importe")
                )

            if "try:" not in contenu:
                violations.append(
                    self._creer_violation(fp, 5, "aucune gestion d'erreur (try absent)")
                )

        # --- .env ----------------------------------------------------------
        if extension == ".env":
            for correspondance in RE_SECRET_ENV.finditer(contenu):
                violations.append(
                    self._creer_violation(
                        fp,
                        1,
                        f"secret en clair : {self._extrait(correspondance.group())}",
                        ligne=self._ligne(contenu, correspondance.start()),
                    )
                )

            correspondance = RE_DEBUG_ACTIF.search(contenu)
            if correspondance:
                violations.append(
                    self._creer_violation(
                        fp,
                        6,
                        "mode debug actif en configuration",
                        ligne=self._ligne(contenu, correspondance.start()),
                    )
                )

            correspondance = RE_HOTES_OUVERTS.search(contenu)
            if correspondance:
                violations.append(
                    self._creer_violation(
                        fp,
                        6,
                        "ALLOWED_HOSTS ouvert a tous les hotes (*)",
                        ligne=self._ligne(contenu, correspondance.start()),
                    )
                )

        # --- JavaScript / TypeScript ---------------------------------------
        if extension in (".js", ".ts"):
            if not any(logger_js in contenu for logger_js in LOGGERS_JS):
                violations.append(
                    self._creer_violation(
                        fp,
                        4,
                        "aucune bibliotheque de logging "
                        f"({', '.join(LOGGERS_JS)}) utilisee",
                    )
                )

            if ".catch(" not in contenu and "try {" not in contenu:
                violations.append(
                    self._creer_violation(
                        fp, 5, "aucune gestion d'erreur (ni try, ni .catch)"
                    )
                )

        # --- Pipeline CI/CD : artefacts non conserves ----------------------
        if extension in (".yaml", ".yml") and self._est_cicd(fp):
            if "artifacts" not in contenu:
                violations.append(
                    self._creer_violation(
                        fp, 9, "pipeline sans conservation d'artefacts"
                    )
                )

        # --- LICENSE vide ---------------------------------------------------
        if fp.nom in ("LICENSE", "LICENCE"):
            if not contenu.strip():
                violations.append(
                    self._creer_violation(fp, 10, "fichier de licence vide")
                )

        return violations

    def _analyser_package_json(self, fp, contenu: str) -> list:
        """Controle les versions de dependances et la licence d'un package.json.

        Args:
            fp: le FichierProjet analyse.
            contenu: son contenu brut.

        Returns:
            Les violations trouvees, [] si le JSON est illisible.
        """
        try:
            donnees = json.loads(contenu)
        except (json.JSONDecodeError, ValueError) as erreur:
            logger.warning("package.json illisible (%s) : %s", fp.chemin, erreur)
            return []

        if not isinstance(donnees, dict):
            logger.warning("package.json inattendu (pas un objet) : %s", fp.chemin)
            return []

        violations = []

        # Regle 2 — versions non figees dans toutes les sections de deps.
        for section in SECTIONS_DEPENDANCES:
            dependances = donnees.get(section)
            if not isinstance(dependances, dict):
                continue
            for paquet, version in dependances.items():
                if isinstance(version, str) and version.strip() in VERSIONS_FLOTTANTES:
                    violations.append(
                        self._creer_violation(
                            fp,
                            2,
                            f"dependance sans version figee : "
                            f"{paquet} = \"{version}\" ({section})",
                            ligne=self._ligne_du_texte(contenu, f'"{paquet}"'),
                        )
                    )

        # Regle 10 — licence absente ou vide.
        licence = donnees.get("license")
        if not (isinstance(licence, str) and licence.strip()):
            violations.append(
                self._creer_violation(fp, 10, "champ license absent du package.json")
            )

        return violations

    # --- Analyseurs LLM ------------------------------------------------------

    def _analyser_llm_complexe(self, fp) -> list:
        """Demande au LLM les seules violations que les regex ne voient pas.

        Args:
            fp: le FichierProjet a analyser.

        Returns:
            Les violations remontees par le LLM pour les regles 1, 4, 5 et 6.
        """
        return self._interroger_llm(fp, PROMPT_COMPLEXE, REGLES_COMPLEXES)

    def _analyser_llm_complet(self, fp) -> list:
        """Demande au LLM un passage sur les 10 Golden Rules.

        Utilise pour les fichiers qu'aucun analyseur deterministe ne couvre.

        Args:
            fp: le FichierProjet a analyser.

        Returns:
            Les violations remontees par le LLM, toutes regles confondues.
        """
        return self._interroger_llm(fp, PROMPT_COMPLET, REGLES_TOUTES)

    def _interroger_llm(self, fp, gabarit: str, regles_autorisees) -> list:
        """Envoie le fichier au LLM, morceau par morceau, et lit sa reponse.

        Args:
            fp: le FichierProjet a analyser.
            gabarit: le prompt a formater avec le nom et le contenu.
            regles_autorisees: ids de Golden Rule acceptes dans la reponse.

        Returns:
            Les violations valides extraites de la reponse, [] si le LLM
            est indisponible ou si sa reponse est inexploitable.
        """
        violations = []

        for morceau in self._morceaux(fp):
            prompt = gabarit.format(nom=fp.nom, contenu=morceau)
            reponse = self.llm.invoquer(prompt)

            # LLM indisponible ou en echec : l'analyse continue sans lui,
            # les analyseurs deterministes ont deja fait leur part.
            if not reponse:
                logger.warning("Pas de reponse du LLM pour %s", fp.chemin)
                continue

            violations.extend(self._lire_reponse_llm(fp, reponse, regles_autorisees))

        return violations

    def _lire_reponse_llm(self, fp, reponse: str, regles_autorisees) -> list:
        """Transforme la reponse JSON du LLM en Violation.

        Chaque entree est validee : une reponse de LLM n'est jamais tenue
        pour acquise (regle inventee, champs manquants, mauvais type).

        Args:
            fp: le FichierProjet concerne.
            reponse: la reponse brute du modele.
            regles_autorisees: ids de Golden Rule acceptes.

        Returns:
            Les violations retenues.
        """
        donnees = self.llm.extraire_json(reponse)
        brutes = donnees.get("violations")

        if not isinstance(brutes, list):
            if donnees:
                logger.warning(
                    "Reponse LLM sans liste 'violations' pour %s", fp.chemin
                )
            return []

        violations = []
        for brute in brutes:
            if not isinstance(brute, dict):
                continue

            # L'id peut arriver en chaine ("1") selon le modele.
            try:
                regle_id = int(brute.get("regle_id"))
            except (TypeError, ValueError):
                logger.debug("Violation LLM sans regle_id exploitable : %s", brute)
                continue

            if regle_id not in regles_autorisees:
                logger.debug(
                    "Regle %s hors perimetre pour %s, ignoree", regle_id, fp.nom
                )
                continue

            probleme = str(brute.get("probleme") or "").strip()
            if not probleme:
                logger.debug("Violation LLM sans description, ignoree : %s", brute)
                continue

            violations.append(
                self._creer_violation(fp, regle_id, probleme, source="llm")
            )

        return violations

    def _morceaux(self, fp) -> list:
        """Decoupe le contenu d'un fichier en fenetres envoyables au LLM.

        Un fichier ordinaire tient dans une seule fenetre. Au-dela de 1 Mo,
        se limiter au debut du fichier reviendrait a n'analyser que son
        en-tete : il est alors decoupe, dans la limite de MAX_MORCEAUX.

        Args:
            fp: le FichierProjet a decouper.

        Returns:
            La liste des morceaux de texte, [] si le fichier est vide.
        """
        contenu = fp.contenu or ""
        if not contenu.strip():
            return []

        if len(contenu) <= SEUIL_DECOUPAGE:
            return [contenu[:FENETRE_LLM]]

        morceaux = [
            contenu[debut:debut + FENETRE_LLM]
            for debut in range(0, len(contenu), FENETRE_LLM)
        ]

        if len(morceaux) > MAX_MORCEAUX:
            logger.warning(
                "Fichier volumineux %s : %d morceaux, seuls les %d premiers "
                "sont analyses",
                fp.chemin,
                len(morceaux),
                MAX_MORCEAUX,
            )
            morceaux = morceaux[:MAX_MORCEAUX]

        return morceaux

    # --- Utilitaires ---------------------------------------------------------

    def _creer_violation(
        self, fp, regle_id: int, probleme: str, source: str = "python", ligne: int = -1
    ) -> Violation:
        """Construit une Violation en reprenant le referentiel des regles.

        Le nom et la severite viennent des Golden Rules, jamais de
        l'analyseur : c'est ce qui garantit un score coherent quelle que
        soit la source de la detection.

        Args:
            fp: le FichierProjet concerne.
            regle_id: identifiant de la Golden Rule violee.
            probleme: description factuelle du probleme.
            source: analyseur a l'origine de la detection.
            ligne: numero de ligne, -1 si la regle porte sur tout le fichier.

        Returns:
            La Violation construite.
        """
        regle = get_rule_by_id(regle_id)
        return Violation(
            fichier=fp.chemin,
            regle_id=regle_id,
            regle_nom=regle.nom if regle else f"Regle {regle_id}",
            severite=regle.severite if regle else "warning",
            probleme=probleme,
            source=source,
            ligne=ligne,
        )

    def _extension(self, fp) -> str:
        """Deduit l'extension d'un fichier a partir de son nom.

        FichierProjet ne porte pas d'extension : elle est recalculee ici
        avec la meme regle que le Crawler, pour que ".env.local" et
        ".env.production" soient traites comme ".env".

        Args:
            fp: le FichierProjet concerne.

        Returns:
            L'extension en minuscules, avec le point ; "" si absente.
        """
        if fp.nom.startswith(".env"):
            return ".env"
        return os.path.splitext(fp.nom)[1].lower()

    def _est_cicd(self, fp) -> bool:
        """Indique si un fichier YAML est un pipeline CI/CD.

        Le Crawler ne distingue pas les pipelines des manifests : ils sont
        tous "devops". La reconnaissance se fait donc sur le nom, le chemin
        (.github/workflows) ou les mots-cles de pipeline dans le contenu.

        Args:
            fp: le FichierProjet concerne.

        Returns:
            True s'il s'agit d'un pipeline CI/CD.
        """
        chemin = fp.chemin.replace(os.sep, "/").lower()
        if ".github/workflows/" in chemin or ".gitlab-ci" in fp.nom.lower():
            return True

        contenu = fp.contenu or ""
        return "stages:" in contenu or "jobs:" in contenu

    def _ligne(self, contenu: str, position: int) -> int:
        """Convertit une position dans le texte en numero de ligne (1-based)."""
        return contenu.count("\n", 0, position) + 1

    def _ligne_du_texte(self, contenu: str, aiguille: str) -> int:
        """Retourne la ligne de la premiere occurrence d'un texte, -1 si absent."""
        position = contenu.find(aiguille)
        return self._ligne(contenu, position) if position != -1 else -1

    def _extrait(self, texte: str, longueur: int = 60) -> str:
        """Raccourcit un extrait de code pour l'inserer dans un message.

        Le contenu d'un secret n'a pas a etre recopie en entier dans le
        rapport : seul son emplacement importe.
        """
        aplati = " ".join(texte.split())
        if len(aplati) <= longueur:
            return aplati
        return aplati[:longueur] + "..."
