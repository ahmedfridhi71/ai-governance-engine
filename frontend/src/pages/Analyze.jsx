/**
 * Analyze — page principale : lancer une analyse et lire son rapport.
 *
 * Trois etats mutuellement exclusifs se disputent la zone de resultat :
 * l'attente, l'erreur et le rapport. Ils sont pilotes par trois variables
 * d'etat remises a zero a chaque soumission, pour qu'un ancien rapport ne
 * reste jamais affiche a cote d'une nouvelle erreur.
 */

import { useState } from 'react'

import AnalyzeForm from '../components/AnalyzeForm'
import RapportCard from '../components/RapportCard'
import ViolationList from '../components/ViolationList'
import { analyzeRepo } from '../services/api'

const ROUGE = '#dc2626'

/** Roue d'attente, animee en SVG pour ne dependre d'aucune feuille de style. */
function Spinner() {
  return (
    <svg width="28" height="28" viewBox="0 0 40 40" aria-hidden="true">
      <circle
        cx="20"
        cy="20"
        r="16"
        fill="none"
        stroke="currentColor"
        strokeOpacity="0.25"
        strokeWidth="6"
      />
      <path
        d="M20 4 a16 16 0 0 1 16 16"
        fill="none"
        stroke="currentColor"
        strokeWidth="6"
        strokeLinecap="round"
      >
        <animateTransform
          attributeName="transform"
          type="rotate"
          from="0 20 20"
          to="360 20 20"
          dur="0.8s"
          repeatCount="indefinite"
        />
      </path>
    </svg>
  )
}

function Analyze() {
  const [loading, setLoading] = useState(false)
  const [rapport, setRapport] = useState(null)
  const [error, setError] = useState('')

  /**
   * Lance l'analyse d'un depot et met a jour les trois etats.
   *
   * @param {string} url - URL du depot, deja nettoyee par le formulaire.
   */
  async function handleSubmit(url) {
    // Table rase : sans cela, le rapport precedent resterait affiche
    // pendant les minutes que dure la nouvelle analyse.
    setLoading(true)
    setError('')
    setRapport(null)

    try {
      const resultat = await analyzeRepo(url)
      setRapport(resultat)
    } catch (erreur) {
      // api.js a deja traduit l'erreur en message lisible.
      setError(erreur.message)
    } finally {
      // Dans finally : le formulaire doit se deverrouiller que l'analyse
      // ait reussi ou echoue.
      setLoading(false)
    }
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
      <h1 style={{ fontSize: '1.8rem', marginTop: 0 }}>Analyser un depot</h1>

      <AnalyzeForm onSubmit={handleSubmit} loading={loading} />

      {loading && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            marginTop: '2rem',
            opacity: 0.85,
          }}
        >
          <Spinner />
          <span>Analyse en cours...</span>
        </div>
      )}

      {error && (
        <div
          role="alert"
          style={{
            marginTop: '2rem',
            border: `1px solid ${ROUGE}`,
            // Fond tres transparent : lisible sur theme clair comme sombre.
            backgroundColor: 'rgba(220, 38, 38, 0.12)',
            color: ROUGE,
            borderRadius: '8px',
            padding: '1rem',
            lineHeight: 1.5,
          }}
        >
          <strong>Analyse impossible</strong>
          <div style={{ marginTop: '0.35rem' }}>{error}</div>
        </div>
      )}

      {rapport && (
        <div style={{ marginTop: '2rem' }}>
          <RapportCard rapport={rapport} />

          <h2 style={{ fontSize: '1.2rem', marginTop: '2rem' }}>
            Violations detectees ({(rapport.violations || []).length})
          </h2>
          <ViolationList violations={rapport.violations} />
        </div>
      )}
    </main>
  )
}

export default Analyze
