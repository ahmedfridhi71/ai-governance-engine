/**
 * ScoreGauge — jauge circulaire du score de conformite.
 *
 * Le score se lit d'un coup d'oeil : la couleur porte l'information avant
 * meme le chiffre. Les seuils reprennent ceux du backend (CalculateScore) :
 * 80 pour "conforme", 50 pour "attention".
 */

// Seuils de bascule de couleur, alignes sur ceux du backend.
const SEUIL_CONFORME = 80
const SEUIL_ATTENTION = 50

const VERT = '#16a34a'
const ORANGE = '#ea580c'
const ROUGE = '#dc2626'

// Geometrie de l'anneau.
const RAYON = 52
const EPAISSEUR = 10
const TAILLE = (RAYON + EPAISSEUR) * 2
const CIRCONFERENCE = 2 * Math.PI * RAYON

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
 * Jauge circulaire affichant le score et le statut.
 *
 * @param {Object} props
 * @param {number} props.score - score de conformite sur 100.
 * @param {string} props.statut - statut derive du score.
 */
function ScoreGauge({ score = 0, statut = '' }) {
  // Un score hors bornes ne doit pas deformer l'anneau.
  const borne = Math.max(0, Math.min(100, Number(score) || 0))
  const couleur = couleurDuScore(borne)

  // La portion non remplie de l'anneau, en longueur d'arc.
  const reste = CIRCONFERENCE * (1 - borne / 100)

  return (
    <div
      style={{
        display: 'inline-flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '0.5rem',
      }}
    >
      <div style={{ position: 'relative', width: TAILLE, height: TAILLE }}>
        <svg
          width={TAILLE}
          height={TAILLE}
          // Depart a midi plutot qu'a 3 heures.
          style={{ transform: 'rotate(-90deg)' }}
          role="img"
          aria-label={`Score de conformite : ${borne} sur 100`}
        >
          {/* Piste de fond, pour donner l'echelle du remplissage. */}
          <circle
            cx={TAILLE / 2}
            cy={TAILLE / 2}
            r={RAYON}
            fill="none"
            stroke="currentColor"
            strokeOpacity="0.15"
            strokeWidth={EPAISSEUR}
          />
          <circle
            cx={TAILLE / 2}
            cy={TAILLE / 2}
            r={RAYON}
            fill="none"
            stroke={couleur}
            strokeWidth={EPAISSEUR}
            strokeLinecap="round"
            strokeDasharray={CIRCONFERENCE}
            strokeDashoffset={reste}
            style={{ transition: 'stroke-dashoffset 0.6s ease' }}
          />
        </svg>

        {/* Chiffre centre, superpose au SVG. */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            lineHeight: 1,
          }}
        >
          <span style={{ fontSize: '2.25rem', fontWeight: 700, color: couleur }}>
            {borne}
          </span>
          <span style={{ fontSize: '0.75rem', opacity: 0.6 }}>/ 100</span>
        </div>
      </div>

      {statut && (
        <span
          style={{
            color: couleur,
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            fontSize: '0.8rem',
          }}
        >
          {statut}
        </span>
      )}
    </div>
  )
}

export default ScoreGauge
