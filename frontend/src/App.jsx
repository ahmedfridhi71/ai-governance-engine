/**
 * App — coquille de l'application : navigation et routage.
 *
 * La barre de navigation occupe toute la largeur, le contenu des pages est
 * centre dans une colonne de 1200 px maximum.
 */

import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'

import Analyze from './pages/Analyze'
import History from './pages/History'
import Home from './pages/Home'
import './App.css'

// Largeur maximale de la colonne de contenu.
const LARGEUR_MAX = '1200px'

// Fond de la barre de navigation. Volontairement sombre dans les deux
// themes : c'est un bandeau, pas une surface de lecture.
const FOND_NAVBAR = '#1a1a1a'

const LIENS = [
  { chemin: '/', libelle: 'Accueil' },
  { chemin: '/analyze', libelle: 'Analyser' },
  { chemin: '/history', libelle: 'Historique' },
]

/**
 * Style d'un lien de navigation.
 *
 * NavLink passe l'etat actif : la page courante est soulignee, ce qui
 * evite a l'utilisateur de deviner ou il se trouve.
 *
 * @param {Object} etat
 * @param {boolean} etat.isActive - true si la route correspond a l'URL.
 * @returns {Object} le style en ligne.
 */
function styleLien({ isActive }) {
  return {
    color: '#fff',
    textDecoration: 'none',
    padding: '0.4rem 0',
    fontWeight: isActive ? 700 : 500,
    borderBottom: `2px solid ${isActive ? '#fff' : 'transparent'}`,
    opacity: isActive ? 1 : 0.8,
  }
}

function App() {
  return (
    <BrowserRouter>
      <nav
        style={{
          backgroundColor: FOND_NAVBAR,
          borderBottom: '1px solid rgba(255, 255, 255, 0.12)',
        }}
      >
        {/* Le bandeau est pleine largeur, son contenu suit la colonne. */}
        <div
          style={{
            maxWidth: LARGEUR_MAX,
            margin: '0 auto',
            padding: '0.9rem 1.5rem',
            display: 'flex',
            alignItems: 'center',
            gap: '1.75rem',
          }}
        >
          <span
            style={{
              color: '#fff',
              fontWeight: 700,
              marginRight: 'auto',
              fontSize: '1rem',
            }}
          >
            AI Governance Engine
          </span>

          {LIENS.map((lien) => (
            <NavLink
              key={lien.chemin}
              to={lien.chemin}
              // end : sans cela, "/" resterait actif sur toutes les routes,
              // puisque tous les chemins commencent par "/".
              end={lien.chemin === '/'}
              style={styleLien}
            >
              {lien.libelle}
            </NavLink>
          ))}
        </div>
      </nav>

      <div style={{ maxWidth: LARGEUR_MAX, margin: '0 auto' }}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/analyze" element={<Analyze />} />
          <Route path="/history" element={<History />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App
