/**
 * AnalyzeForm — saisie de l'URL du depot a analyser.
 *
 * Le formulaire se verrouille pendant l'analyse : celle-ci dure plusieurs
 * minutes (clone, Checkov, appels LLM) et un second envoi relancerait tout
 * le pipeline en parallele.
 */

import { useState } from 'react'

/**
 * Roue d'attente. Anime en SVG plutot qu'en CSS pour rester autonome :
 * le composant n'a besoin d'aucune feuille de style externe.
 */
function Spinner() {
  return (
    <svg width="16" height="16" viewBox="0 0 40 40" aria-hidden="true">
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

/**
 * Formulaire de lancement d'analyse.
 *
 * @param {Object} props
 * @param {Function} props.onSubmit - appele avec l'URL saisie.
 * @param {boolean} props.loading - true pendant l'analyse en cours.
 */
function AnalyzeForm({ onSubmit, loading = false }) {
  const [url, setUrl] = useState('')

  const urlNettoyee = url.trim()
  // Rien a envoyer, ou analyse deja en cours.
  const desactive = loading || !urlNettoyee

  /**
   * Intercepte l'envoi du formulaire.
   *
   * @param {Event} evenement - l'evenement submit.
   */
  function envoyer(evenement) {
    // Sans cela, le navigateur rechargerait la page.
    evenement.preventDefault()

    if (desactive) return
    onSubmit(urlNettoyee)
  }

  return (
    <form
      onSubmit={envoyer}
      style={{
        display: 'flex',
        gap: '0.5rem',
        flexWrap: 'wrap',
        alignItems: 'center',
      }}
    >
      <input
        type="text"
        value={url}
        onChange={(evenement) => setUrl(evenement.target.value)}
        // Verrouille pendant l'analyse : la valeur soumise ne doit pas
        // changer sous les pieds de la requete en cours.
        disabled={loading}
        placeholder="https://github.com/organisation/projet"
        aria-label="URL du depot Git a analyser"
        style={{
          flex: '1 1 20rem',
          padding: '0.6rem 0.8rem',
          borderRadius: '8px',
          border: '1px solid rgba(128, 128, 128, 0.4)',
          background: 'transparent',
          color: 'inherit',
          fontSize: '0.95rem',
        }}
      />

      <button
        type="submit"
        disabled={desactive}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.6rem 1.2rem',
          borderRadius: '8px',
          border: '1px solid transparent',
          fontSize: '0.95rem',
          fontWeight: 600,
          cursor: desactive ? 'not-allowed' : 'pointer',
          opacity: desactive ? 0.6 : 1,
        }}
      >
        {loading && <Spinner />}
        {loading ? 'Analyse en cours...' : 'Analyser'}
      </button>

      {loading && (
        <span style={{ fontSize: '0.8rem', opacity: 0.7, flexBasis: '100%' }}>
          Clone, analyse statique et appels LLM : comptez plusieurs minutes.
        </span>
      )}
    </form>
  )
}

export default AnalyzeForm
