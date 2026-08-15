# Image du backend — AI Governance Engine.
#
# Contexte de build attendu : le dossier backend/ lui-meme.
#     docker build -t governance-backend ./backend
#
# Le code est copie dans /app/backend/ et non directement dans /app :
# uvicorn demarre "backend.main:app", il faut donc que "backend" soit un
# paquet importable depuis le repertoire de travail.

FROM python:3.11-slim

# git : CloneRepo lance un clone via GitPython, qui appelle le binaire git.
# ca-certificates : sans lui, le clone HTTPS et les appels a l'API Gemini
# echouent sur une erreur de certificat.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Environnement virtuel dedie, place hors de /app pour qu'un montage de
# volume sur le code (compose en developpement) ne le masque pas.
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv "$VIRTUAL_ENV"

# Le venv en tete du PATH. Indispensable et pas seulement pour pip :
# CheckovClient lance ["checkov", "--version"] en sous-processus et
# resout donc le binaire par le PATH. Sans cette ligne, l'analyse DevOps
# se declarerait silencieusement indisponible et ne remonterait rien.
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app

# Les dependances d'abord, le code ensuite : cette couche n'est
# reconstruite que si requirements.txt change.
COPY requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/backend/requirements.txt

# checkov est deja epingle dans requirements.txt (3.2.257). On ne le
# reinstalle pas, on verifie qu'il repond bien depuis le PATH : mieux
# vaut echouer ici, au build, qu'a la premiere analyse en production.
RUN checkov --version

# Tout le contenu du dossier backend, y compris .env s'il existe. Passer
# par COPY . evite un COPY dedie qui echouerait quand le fichier est absent.
COPY . /app/backend/

# Logs non bufferises : sans cela, la sortie d'uvicorn n'apparait dans
# `docker logs` que par blocs, ce qui rend une analyse longue illisible.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
