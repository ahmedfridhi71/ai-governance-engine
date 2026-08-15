/**
 * ViolationList — liste detaillee des violations d'un rapport.
 *
 * Chaque violation est presentee comme une fiche : le constat factuel en
 * tete, puis l'explication et la correction redigees par le LLM. Ces deux
 * derniers champs sont facultatifs — ils restent vides quand le LLM est
 * indisponible ou quand la violation depasse le plafond d'enrichissement.
 */

// Couleur d'accent par severite. Les valeurs viennent du Domain backend.
const COULEURS_SEVERITE = {
  critique: '#dc2626',
  warning: '#ea580c',
}

// Severite inattendue : gris neutre plutot qu'une couleur trompeuse.
const COULEUR_INCONNUE = '#6b7280'

/**
 * Badge colore portant la severite.
 *
 * @param {Object} props
 * @param {string} props.severite - "critique" ou "warning".
 */
function BadgeSeverite({ severite }) {
  const couleur = COULEURS_SEVERITE[severite] || COULEUR_INCONNUE

  return (
    <span
      style={{
        backgroundColor: couleur,
        color: '#fff',
        borderRadius: '999px',
        padding: '0.15rem 0.6rem',
        fontSize: '0.7rem',
        fontWeight: 700,
        textTransform: 'uppercase',
        letterSpacing: '0.04em',
        whiteSpace: 'nowrap',
      }}
    >
      {severite || 'inconnue'}
    </span>
  )
}

/**
 * Bloc facultatif : n'affiche rien si le texte est vide.
 *
 * @param {Object} props
 * @param {string} props.titre - intitule du bloc.
 * @param {string} props.texte - contenu, eventuellement vide.
 */
function Section({ titre, texte }) {
  if (!texte) return null

  return (
    <div style={{ marginTop: '0.75rem' }}>
      <div
        style={{
          fontSize: '0.7rem',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          opacity: 0.6,
          marginBottom: '0.25rem',
        }}
      >
        {titre}
      </div>
      {/* pre-wrap : les corrections du LLM contiennent des extraits de code
          dont les sauts de ligne et l'indentation portent du sens. */}
      <div
        style={{
          whiteSpace: 'pre-wrap',
          fontSize: '0.9rem',
          lineHeight: 1.5,
        }}
      >
        {texte}
      </div>
    </div>
  )
}

/**
 * Une fiche de violation.
 *
 * @param {Object} props
 * @param {Object} props.violation - la violation a afficher.
 */
function Violation({ violation }) {
  const couleur = COULEURS_SEVERITE[violation.severite] || COULEUR_INCONNUE

  return (
    <li
      style={{
        listStyle: 'none',
        border: '1px solid rgba(128, 128, 128, 0.3)',
        // Liseré de severite : reperage vertical rapide dans une longue liste.
        borderLeft: `4px solid ${couleur}`,
        borderRadius: '8px',
        padding: '1rem',
        marginBottom: '0.75rem',
        textAlign: 'left',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.6rem',
          flexWrap: 'wrap',
        }}
      >
        <BadgeSeverite severite={violation.severite} />
        <strong style={{ fontSize: '0.95rem' }}>{violation.regle_nom}</strong>
        <span style={{ fontSize: '0.75rem', opacity: 0.6 }}>
          regle {violation.regle_id}
          {violation.source && ` · ${violation.source}`}
        </span>
      </div>

      <div
        style={{
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
          fontSize: '0.8rem',
          opacity: 0.75,
          marginTop: '0.4rem',
          wordBreak: 'break-all',
        }}
      >
        {violation.fichier}
        {/* -1 signifie "regle portant sur tout le fichier" : ne pas l'afficher. */}
        {violation.ligne > 0 && `:${violation.ligne}`}
      </div>

      <div style={{ marginTop: '0.5rem', fontSize: '0.95rem' }}>
        {violation.probleme}
      </div>

      <Section titre="Explication" texte={violation.explication} />
      <Section titre="Correction" texte={violation.correction} />
    </li>
  )
}

/**
 * Liste des violations d'un rapport.
 *
 * @param {Object} props
 * @param {Array} props.violations - les violations a afficher.
 */
function ViolationList({ violations = [] }) {
  if (!violations.length) {
    return (
      <p style={{ opacity: 0.7 }}>
        Aucune violation detectee.
      </p>
    )
  }

  return (
    <ul style={{ padding: 0, margin: 0 }}>
      {violations.map((violation, index) => (
        // Pas d'identifiant stable cote backend : la position dans la liste
        // fait office de cle, la liste n'etant ni triee ni filtree ici.
        <Violation
          key={`${violation.fichier}-${violation.regle_id}-${index}`}
          violation={violation}
        />
      ))}
    </ul>
  )
}

export default ViolationList
