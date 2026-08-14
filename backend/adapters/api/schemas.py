"""
Schemas de l'API — couche Adapters.

Contrat d'entree et de sortie de l'API FastAPI. Ces modeles Pydantic sont
la frontiere entre le monde exterieur et le Domain : ils valident ce qui
entre et fixent la forme de ce qui sort, sans que les entites du Domain
aient a connaitre HTTP ou JSON.

Les champs reprennent exactement ceux des dataclasses Violation et
Rapport, pour qu'un rapport produit par GenerateReport se serialise sans
transformation :

    RapportResponse(**rapport_dict)

Dependance : pydantic v2.
"""

from typing import List

from pydantic import BaseModel, Field, field_validator

# Schemas d'URL acceptes pour un depot Git.
SCHEMAS_URL = ("http://", "https://", "git@", "ssh://", "git://")


class AnalyzeRequest(BaseModel):
    """Demande d'analyse d'un depot Git."""

    # URL du depot a cloner puis analyser.
    # Exemple : "https://github.com/sofrecom/mon-projet"
    url: str = Field(
        ...,
        description="URL du depot Git a analyser",
        examples=["https://github.com/sofrecom/mon-projet"],
    )

    @field_validator("url")
    @classmethod
    def valider_url(cls, valeur: str) -> str:
        """Rejette les URL vides ou d'un schema inattendu.

        Cette URL finit en argument de `git clone` : la controler ici
        evite de transmettre n'importe quelle chaine a la couche
        Infrastructure, et rend l'erreur lisible cote client (422) plutot
        qu'en echec de clone.

        Args:
            valeur: l'URL soumise.

        Returns:
            L'URL debarrassee de ses espaces.

        Raises:
            ValueError: si l'URL est vide ou d'un schema non supporte.
        """
        url = valeur.strip()

        if not url:
            raise ValueError("URL du depot manquante")

        if not url.startswith(SCHEMAS_URL):
            raise ValueError(
                "URL de depot non supportee : elle doit commencer par "
                + ", ".join(SCHEMAS_URL)
            )

        return url


class ViolationResponse(BaseModel):
    """Une violation telle qu'exposee par l'API."""

    # Chemin du fichier concerne.
    fichier: str

    # Identifiant de la Golden Rule violee, de 1 a 10.
    regle_id: int

    # Nom court de la Golden Rule violee.
    regle_nom: str

    # "critique" (-15 points) ou "warning" (-5 points).
    severite: str

    # Description factuelle du probleme detecte.
    probleme: str

    # Explication pedagogique redigee par le LLM.
    # Vide tant que l'enrichissement n'a pas eu lieu.
    explication: str = Field(default="")

    # Correction proposee, redigee par le LLM.
    # Vide tant que l'enrichissement n'a pas eu lieu.
    correction: str = Field(default="")

    # Analyseur a l'origine de la detection : "checkov", "python" ou "llm".
    source: str = Field(default="")

    # Numero de ligne, -1 lorsque la regle porte sur tout le fichier.
    ligne: int = Field(default=-1)


class ResumeResponse(BaseModel):
    """Synthese chiffree d'une analyse."""

    # Nombre de violations de severite "critique".
    critiques: int

    # Nombre de violations de severite "warning".
    warnings: int

    # Nombre de Golden Rules sans aucune violation.
    conformes: int


class RapportResponse(BaseModel):
    """Rapport de conformite complet, retourne par l'API."""

    # URL du depot analyse.
    repo_url: str

    # Score de conformite sur 100.
    score: int

    # Statut derive du score : "conforme", "attention" ou "non conforme".
    statut: str

    # Violations retenues, apres deduplication et enrichissement.
    violations: List[ViolationResponse] = Field(default_factory=list)

    # Nombre de fichiers trouves dans le depot clone.
    total_fichiers: int = Field(default=0)

    # Nombre de fichiers reellement analyses, apres filtrage.
    fichiers_analyses: int = Field(default=0)

    # Date et heure de l'analyse au format ISO 8601.
    date_analyse: str = Field(default="")

    # Synthese chiffree de l'analyse.
    resume: ResumeResponse
