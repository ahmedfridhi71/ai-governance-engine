# Image du frontend — AI Governance Engine.
#
# Contexte de build attendu : le dossier frontend/ lui-meme.
#     docker build -t governance-frontend ./frontend
#
# Deux etapes : Node compile l'application, Nginx sert le resultat. L'image
# finale ne contient ni Node, ni node_modules, ni le code source — seulement
# les fichiers statiques produits par Vite.

# --- Etape 1 : compilation ---------------------------------------------------
FROM node:18-alpine AS builder

WORKDIR /app

# Les manifestes d'abord : cette couche n'est reconstruite que si les
# dependances changent, pas a chaque modification du code.
COPY package*.json ./
RUN npm install

COPY . .

# Vite remplace import.meta.env.VITE_* par sa valeur AU MOMENT DU BUILD :
# ces variables n'existent plus a l'execution. L'URL de l'API doit donc
# etre fournie ici, pas au demarrage du conteneur.
#
# La valeur par defaut ne vaut que pour un backend joignable depuis le
# navigateur sur localhost:8000. Derriere un reverse proxy, passer par
# exemple : --build-arg VITE_API_URL=/api/v1
ARG VITE_API_URL=http://localhost:8000/api/v1
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# --- Etape 2 : service des fichiers statiques --------------------------------
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx-frontend.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
