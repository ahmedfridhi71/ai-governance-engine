/**
 * Home — page d'accueil.
 *
 * Presente le moteur en quelques lignes et dirige vers l'analyse.
 * Aucun appel a l'API : cette page doit s'afficher meme backend arrete.
 */

import { useNavigate } from 'react-router-dom'

// Les trois analyseurs, tels que le backend les orchestre.
const ANALYSEURS = [
  {
    titre: 'Checkov',
    texte: "Analyse statique des manifests Kubernetes, Terraform et Docker.",
  },
  {
    titre: 'Analyse deterministe',
    texte: 'Secrets en clair, versions non figees, logs, gestion des erreurs.',
  },
  {
    titre: 'LLM',
    texte: "Les defauts qu'aucune regle fixe ne detecte : SQL concatene, endpoints sans authentification.",
  },
]

function Home() {
  const naviguer = useNavigate()

  return (
    <main
      style={{
        maxWidth: '48rem',
        margin: '0 auto',
        padding: '3rem 1.5rem',
        textAlign: 'left',
      }}
    >
      <h1 style={{ fontSize: '2.5rem', margin: 0, lineHeight: 1.15 }}>
        AI Governance Engine
      </h1>

      <p style={{ fontSize: '1.2rem', opacity: 0.85, marginTop: '0.75rem' }}>
        Analysez la conformite de vos projets IT
      </p>

      <p style={{ lineHeight: 1.6, marginTop: '1.5rem' }}>
        Le moteur clone un depot Git, inventorie ses fichiers et les confronte
        a dix Golden Rules de gouvernance : secrets en clair, versionnement,
        documentation, logs, gestion des erreurs, securite des acces,
        disponibilite, limites de ressources, sauvegarde et conformite. Il en
        tire un score sur 100, un statut, et pour chaque manquement une
        explication et une correction.
      </p>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(13rem, 1fr))',
          gap: '1rem',
          marginTop: '2rem',
        }}
      >
        {ANALYSEURS.map((analyseur) => (
          <div
            key={analyseur.titre}
            style={{
              border: '1px solid rgba(128, 128, 128, 0.3)',
              borderRadius: '8px',
              padding: '1rem',
            }}
          >
            <div style={{ fontWeight: 700, marginBottom: '0.35rem' }}>
              {analyseur.titre}
            </div>
            <div style={{ fontSize: '0.9rem', opacity: 0.8, lineHeight: 1.5 }}>
              {analyseur.texte}
            </div>
          </div>
        ))}
      </div>

      <button
        type="button"
        onClick={() => naviguer('/analyze')}
        style={{
          marginTop: '2.5rem',
          padding: '0.8rem 1.75rem',
          borderRadius: '8px',
          border: '1px solid transparent',
          fontSize: '1rem',
          fontWeight: 600,
          cursor: 'pointer',
        }}
      >
        Commencer l&apos;analyse
      </button>
    </main>
  )
}

export default Home
