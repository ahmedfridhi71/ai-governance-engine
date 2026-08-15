/**
 * History — historique des analyses enregistrees.
 *
 * Liste les derniers rapports persistes en base, et deplie le detail de
 * celui que l'on selectionne. GET /rapports renvoie deja les documents
 * complets, violations comprises : la selection n'appelle donc pas l'API,
 * elle se contente d'afficher l'objet deja charge.
 */

import { useEffect, useState } from 'react'

import RapportCard from '../components/RapportCard'
import ViolationList from '../components/ViolationList'
import { getRapports } from '../services/api'

const ROUGE = '#dc2626'
const ORANGE = '#ea580c'
const VERT = '#16a34a'

// Memes seuils que le backend (CalculateScore).
const SEUIL_CONFORME = 80
const SEUIL_ATTENTION = 50

/**
 * Couleur associee a un score.
 *
 * @param {number} score - score sur 100.
 * @returns {string} la couleur hexadecimale.
 */
function couleurDuScore(score) {
  if (score >= SEUIL_CONFORME) return VERT
  if (score >= SEUIL_ATTENTION) return ORANGE
  return ROUGE
}

/**
 * Met en forme une date ISO pour un lecteur francophone.
 *
 * @param {string} iso - date au format ISO 8601.
 * @returns {string} la date lisible, ou "" si absente ou invalide.
 */
function formaterDate(iso) {
  if (!iso) return ''

  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso

  return date.toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
}

/**
 * Une ligne cliquable de l'historique.
 *
 * @param {Object} props
 * @param {Object} props.rapport - le rapport resume.
 * @param {boolean} props.selectionne - true si son detail est deplie.
 * @param {Function} props.onClick - appele au clic.
 */
function Ligne({ rapport, selectionne, onClick }) {
  const couleur = couleurDuScore(rapport.score)

  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '1rem',
        width: '100%',
        textAlign: 'left',
        padding: '0.9rem 1rem',
        marginBottom: '0.5rem',
        borderRadius: '8px',
        border: `1px solid ${selectionne ? couleur : 'rgba(128, 128, 128, 0.3)'}`,
        background: 'transparent',
        color: 'inherit',
        cursor: 'pointer',
        font: 'inherit',
      }}
    >
      <span
        style={{
          color: couleur,
          fontWeight: 700,
          fontSize: '1.25rem',
          minWidth: '3rem',
        }}
      >
        {rapport.score}
      </span>

      <span style={{ flex: 1, minWidth: 0 }}>
        <span
          style={{
            display: 'block',
            wordBreak: 'break-all',
            fontSize: '0.95rem',
          }}
        >
          {rapport.repo_url}
        </span>
        <span style={{ fontSize: '0.78rem', opacity: 0.7 }}>
          {rapport.statut}
          {rapport.date_analyse && ` · ${formaterDate(rapport.date_analyse)}`}
        </span>
      </span>

      <span style={{ fontSize: '0.75rem', opacity: 0.6, whiteSpace: 'nowrap' }}>
        {selectionne ? 'masquer' : 'details'}
      </span>
    </button>
  )
}

function History() {
  const [rapports, setRapports] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  // Identifiant du rapport deplie, null si aucun.
  const [selection, setSelection] = useState(null)

  useEffect(() => {
    // Garde-fou contre une mise a jour apres demontage : l'utilisateur
    // peut quitter la page avant la fin de la requete.
    let actif = true

    async function charger() {
      try {
        const resultat = await getRapports()
        if (actif) setRapports(resultat)
      } catch (erreur) {
        if (actif) setError(erreur.message)
      } finally {
        if (actif) setLoading(false)
      }
    }

    charger()
    return () => {
      actif = false
    }
  }, [])

  /**
   * Identifiant d'affichage d'un rapport.
   *
   * Mongo fournit "_id" ; on retombe sur la position pour les rapports qui
   * n'en auraient pas (base indisponible, document ancien).
   *
   * @param {Object} rapport - le rapport concerne.
   * @param {number} index - sa position dans la liste.
   * @returns {string} une cle utilisable.
   */
  function identifiant(rapport, index) {
    return rapport._id || `${rapport.repo_url}-${index}`
  }

  return (
    <main
      style={{
        maxWidth: '56rem',
        margin: '0 auto',
        padding: '2.5rem 1.5rem',
        textAlign: 'left',
      }}
    >
      <h1 style={{ fontSize: '1.8rem', marginTop: 0 }}>Historique des analyses</h1>

      {loading && <p style={{ opacity: 0.8 }}>Chargement...</p>}

      {error && (
        <div
          role="alert"
          style={{
            border: `1px solid ${ROUGE}`,
            backgroundColor: 'rgba(220, 38, 38, 0.12)',
            color: ROUGE,
            borderRadius: '8px',
            padding: '1rem',
            lineHeight: 1.5,
          }}
        >
          <strong>Historique indisponible</strong>
          <div style={{ marginTop: '0.35rem' }}>{error}</div>
        </div>
      )}

      {!loading && !error && rapports.length === 0 && (
        <p style={{ opacity: 0.7 }}>Aucune analyse effectuee</p>
      )}

      {rapports.map((rapport, index) => {
        const cle = identifiant(rapport, index)
        const ouvert = selection === cle

        return (
          <div key={cle}>
            <Ligne
              rapport={rapport}
              selectionne={ouvert}
              // Un second clic sur la meme ligne replie le detail.
              onClick={() => setSelection(ouvert ? null : cle)}
            />

            {ouvert && (
              <div style={{ margin: '0.5rem 0 1.5rem' }}>
                <RapportCard rapport={rapport} />

                <h2 style={{ fontSize: '1.1rem', marginTop: '1.5rem' }}>
                  Violations detectees ({(rapport.violations || []).length})
                </h2>
                <ViolationList violations={rapport.violations} />
              </div>
            )}
          </div>
        )
      })}
    </main>
  )
}

export default History
