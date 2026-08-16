/**
 * Service d'appel au backend — AI Governance Engine.
 *
 * Seul point du frontend qui connait les URL de l'API. Les composants
 * appellent ces fonctions et n'ont jamais a manipuler axios ni a savoir
 * comment le backend structure ses erreurs.
 *
 * Chaque fonction leve une Error porteuse d'un message lisible en cas
 * d'echec : les composants n'ont qu'a l'afficher.
 */

import axios from 'axios'

// URL de l'API. Surchargeable par VITE_API_URL au build : en conteneur,
// le backend n'est pas sur localhost du point de vue du navigateur.
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

// Une analyse enchaine un clone, Checkov et des dizaines d'appels LLM :
// elle se compte en minutes. 30 minutes, la ou axios ne mettrait aucune
// limite par defaut. Doit rester aligne sur les proxy_*_timeout de
// nginx/nginx.conf : la limite la plus courte des deux l'emporte.
const TIMEOUT_MS = 1800000

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: TIMEOUT_MS,
})

/**
 * Traduit une erreur axios en message lisible par un humain.
 *
 * Trois cas distincts, qui appellent trois reactions differentes de la
 * part de l'utilisateur : le serveur a repondu une erreur, le serveur
 * n'a pas repondu du tout, ou la requete etait mal formee.
 *
 * @param {Error} erreur - l'erreur levee par axios.
 * @param {string} action - ce que l'on tentait de faire, pour le message.
 * @returns {Error} une Error au message explicite.
 */
function erreurLisible(erreur, action) {
  // Delai depasse : distinct d'une absence de reponse, car l'analyse
  // continue peut-etre cote serveur.
  if (erreur.code === 'ECONNABORTED') {
    return new Error(
      `${action} : le serveur n'a pas repondu dans les ${TIMEOUT_MS / 1000} secondes. ` +
        `L'analyse est peut-etre encore en cours.`,
    )
  }

  // Le serveur a repondu, mais en erreur.
  if (erreur.response) {
    const { status, data } = erreur.response
    return new Error(`${action} : ${detailErreur(data)} (HTTP ${status})`)
  }

  // Requete partie, aucune reponse : backend arrete, mauvaise URL, CORS.
  if (erreur.request) {
    return new Error(
      `${action} : le serveur est injoignable a l'adresse ${API_BASE_URL}. ` +
        `Verifiez qu'il est demarre.`,
    )
  }

  return new Error(`${action} : ${erreur.message}`)
}

/**
 * Extrait le message d'erreur du corps d'une reponse FastAPI.
 *
 * FastAPI renvoie une chaine dans `detail` pour une HTTPException, mais
 * un tableau d'objets pour une erreur de validation (422).
 *
 * @param {*} data - le corps de la reponse.
 * @returns {string} le message a afficher.
 */
function detailErreur(data) {
  if (!data || !data.detail) {
    return 'erreur inattendue du serveur'
  }

  if (typeof data.detail === 'string') {
    return data.detail
  }

  // Erreur de validation : on concatene les messages de chaque champ.
  if (Array.isArray(data.detail)) {
    return data.detail.map((item) => item.msg || String(item)).join(' ; ')
  }

  return String(data.detail)
}

/**
 * Lance l'analyse de conformite d'un depot Git.
 *
 * Operation longue : le backend clone le depot, lance Checkov, l'analyse
 * Python et le LLM avant de repondre.
 *
 * @param {string} url - URL du depot a analyser.
 * @returns {Promise<Object>} le rapport de conformite complet.
 * @throws {Error} si l'analyse echoue.
 */
export async function analyzeRepo(url) {
  try {
    const reponse = await api.post('/analyze', { url })
    return reponse.data
  } catch (erreur) {
    throw erreurLisible(erreur, "Echec de l'analyse du depot")
  }
}

/**
 * Recupere les derniers rapports enregistres.
 *
 * @returns {Promise<Array>} les rapports, du plus recent au plus ancien.
 * @throws {Error} si la lecture echoue.
 */
export async function getRapports() {
  try {
    const reponse = await api.get('/rapports')
    return reponse.data
  } catch (erreur) {
    throw erreurLisible(erreur, 'Echec du chargement des rapports')
  }
}

/**
 * Recupere un rapport precis par son identifiant.
 *
 * @param {string} id - identifiant du rapport.
 * @returns {Promise<Object>} le rapport demande.
 * @throws {Error} si le rapport est introuvable ou la lecture echoue.
 */
export async function getRapportById(id) {
  try {
    const reponse = await api.get(`/rapports/${id}`)
    return reponse.data
  } catch (erreur) {
    throw erreurLisible(erreur, `Echec du chargement du rapport ${id}`)
  }
}

/**
 * Verifie que le backend repond.
 *
 * @returns {Promise<Object>} l'etat du serveur, ex: { status: "ok" }.
 * @throws {Error} si le serveur est injoignable.
 */
export async function getHealth() {
  try {
    const reponse = await api.get('/health')
    return reponse.data
  } catch (erreur) {
    throw erreurLisible(erreur, 'Le serveur ne repond pas')
  }
}

export default api
