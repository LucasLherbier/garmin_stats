# garmin_stats — version desktop

Même fonctionnement, mêmes onglets, mêmes routes, mêmes appels API.
Seule la présentation change à partir de **1024 px** : en dessous, le front
mobile actuel s'affiche à l'identique (aucun style mobile modifié).

Build vérifié : `npm run build` (tsc + vite) passe sur le HEAD du repo
(`ea94f07`) avec ces fichiers appliqués.

## Installation

Copie les fichiers aux mêmes chemins dans le repo, c'est tout :

| Fichier | Statut |
|---|---|
| `frontend/src/hooks/useMediaQuery.ts` | nouveau |
| `frontend/src/components/SideNav.tsx` | nouveau |
| `frontend/src/pages/OverviewDesktop.tsx` | nouveau |
| `frontend/src/components/Layout.tsx` | modifié (+ SideNav dans le shell) |
| `frontend/src/components/BottomNav.tsx` | modifié (les items deviennent `NAV_ITEMS`, exportés pour la sidebar) |
| `frontend/src/pages/OverviewPage.tsx` | modifié (la page actuelle devient `OverviewMobile`, un wrapper choisit selon l'écran) |
| `frontend/src/theme.css` | section « DESKTOP LAYOUT » ajoutée à la fin, rien d'existant touché |

## Ce que ça donne sur ordi

- **Sidebar fixe à gauche** (252 px) : logo + nom, les 7 onglets avec
  icônes et labels complets (Dashboard, Swim, Bike, Run, Race prep,
  Results, Stats), onglet actif en pilule lime — le même traitement que
  la pilule active de la nav mobile. En bas : carte de synchro Garmin
  (le même `SyncButton`, avec son mot de passe et son retour d'état).
- **La BottomNav disparaît** sur desktop (CSS uniquement, elle reste
  dans le DOM pour le mobile).
- **Toutes les pages passent de 430 px à 1180 px** de large, titres plus
  grands. Les graphes Recharts, tableaux et listes existants profitent
  de la largeur sans modification.

## Le Home desktop (le gros morceau)

Nouvelle composition en grille 12 colonnes, avec exactement les mêmes
données que le mobile (`weeklyTotals`, `volumeChart`, `benchmarks`,
`activityCalendar`) :

- **Hero « This week » (7 col.)** : durée totale en très grand, mix-bar
  des sports, sessions, delta vs semaine dernière, et les cartes par
  sport (Swim/Bike/Run km) en une rangée.
- **Calendrier « When you train » (5 col.)** à droite du hero, au lieu
  d'être relégué sous le pli.
- **Training explorer (7 col.)** : les 3 contrôles (Granularity /
  Metric / Range) sur **une seule ligne** avec labels, et le graphe de
  volume en hauteur 320 px (contre 210 sur mobile).
- **Benchmarks (5 col.)** à droite de l'explorer, en pile verticale.
- En-tête : « Home » + la date du jour en sous-titre + bouton sync.

## Comment c'est branché

- `useIsDesktop()` = `matchMedia('(min-width: 1024px)')`, réactif au
  redimensionnement de la fenêtre (pas de sniffing d'user-agent).
- `OverviewPage` choisit `OverviewDesktop` ou `OverviewMobile` ;
  la version mobile est ton code actuel, inchangé caractère pour
  caractère (juste renommée en interne).
- Le shell (`Layout`) rend toujours SideNav + Outlet + BottomNav ;
  le CSS décide quoi afficher selon la largeur.

## Pistes pour la suite (non faites)

- Pages Sport/Stats desktop dédiées (grilles de graphes 2×2, tableaux
  plus denses) sur le même patron que le Home.
- Raccourcir le bundle : le warning vite « chunk > 500 kB » existe déjà ;
  un `lazy()` sur les routes desktop/mobile réduirait le chargement
  initial des deux côtés.
