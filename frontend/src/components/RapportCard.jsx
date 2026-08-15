/**
 * RapportCard — synthese d'un rapport de conformite.
 *
 * Vue d'ensemble sans le detail des violations : score, repartition par
 * severite et volumetrie. Le detail est du ressort de ViolationList.
 */

import ScoreGauge from './ScoreGauge'

const ROUGE = '#dc2626'
const ORANGE = '#ea580c'
const VERT = '#16a34a'

/**
 * Met en forme une date ISO pour un lecteur francophone.
 *
 * @param {string} iso - date au format ISO 8601.
 * @returns {string} la date lisible, ou "" si elle est absente ou invalide.
 */
function formaterDate(iso) {
  if (!iso) return ''

  const date = new Date(iso)
  // Une date invalide rendrait "Invalid Date" : mieux vaut l'ISO brute.
  if (Number.isNaN(date.getTime())) return iso

  return date.toLocaleString('fr-FR', {
    dateStyle: 'long',
    timeStyle: 'short',
  })
}

/**
 * Un chiffre du resume, avec son intitule.
 *
 * @param {Object} props
 * @param {number} props.valeur - le nombre a mettre en avant.
 * @param {string} props.libelle - ce qu'il compte.
 * @param {string} props.couleur - couleur d'accent.
 */
function Compteur({ valeur, libelle, couleur }) {
  return (
    <div
      style={{
        border: '1px solid rgba(128, 128, 128, 0.3)',
        borderRadius: '8px',
        padding: '0.6rem 1rem',
        minWidth: '5.5rem',
        textAlign: 'center',
      }}
    >
      <div style={{ fontSize: '1.5rem', fontWeight: 700, color: couleur }}>
        {valeur}
      </div>
      <div style={{ fontSize: '0.7rem', opacity: 0.7, textTransform: 'uppercase' }}>
        {libelle}
      </div>
    </div>
  )
}

/**
 * Carte de synthese d'un rapport.
 *
 * @param {Object} props
 * @param {Object} props.rapport - le rapport retourne par l'API.
 */
function RapportCard({ rapport }) {
  if (!rapport) return null

  // Un rapport peut arriver sans resume (document ancien, base incomplete) :
  // on retombe sur des zeros plutot que de casser l'affichage.
  const resume = rapport.resume || {}
  const date = formaterDate(rapport.date_analyse)

  return (
    <section
      style={{
        border: '1px solid rgba(128, 128, 128, 0.3)',
        borderRadius: '12px',
        padding: '1.5rem',
        textAlign: 'left',
      }}
    >
      <div style={{ marginBottom: '1.25rem' }}>
        <h2
          style={{
            margin: 0,
            fontSize: '1.1rem',
            wordBreak: 'break-all',
          }}
        >
          {rapport.repo_url}
        </h2>
        {date && (
          <div style={{ fontSize: '0.8rem', opacity: 0.7, marginTop: '0.25rem' }}>
            Analyse du {date}
          </div>
        )}
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '2rem',
          flexWrap: 'wrap',
        }}
      >
        <ScoreGauge score={rapport.score} statut={rapport.statut} />

        <div
          style={{
            display: 'flex',
            gap: '0.75rem',
            flexWrap: 'wrap',
          }}
        >
          <Compteur
            valeur={resume.critiques ?? 0}
            libelle="critiques"
            couleur={ROUGE}
          />
          <Compteur
            valeur={resume.warnings ?? 0}
            libelle="warnings"
            couleur={ORANGE}
          />
          <Compteur
            valeur={resume.conformes ?? 0}
            libelle="regles OK"
            couleur={VERT}
          />
        </div>
      </div>

      <div
        style={{
          marginTop: '1.25rem',
          paddingTop: '1rem',
          borderTop: '1px solid rgba(128, 128, 128, 0.25)',
          fontSize: '0.85rem',
          opacity: 0.8,
        }}
      >
        {rapport.fichiers_analyses ?? 0} fichier(s) analyse(s)
        {' sur '}
        {rapport.total_fichiers ?? 0}
        {' · '}
        {(rapport.violations || []).length} violation(s) retenue(s)
      </div>
    </section>
  )
}

export default RapportCard
