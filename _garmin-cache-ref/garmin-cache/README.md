# garmin_stats — kit cache (navigation instantanée)

## Diagnostic (vérifié dans le code)

- **Front : aucun cache.** Chaque page fetch à chaque montage ; revenir
  en arrière rejoue toutes les requêtes (Home = 4 appels, une page Race
  = le détail + les listes par sport).
- **Back : un cache existe** (`@lru_cache` sur `query_bigquery`) mais
  **plafonné à 64 requêtes SQL** pour toute l'app — quelques pages
  visitées et il sature, les requêtes BigQuery (plusieurs secondes
  chacune, ~10 pour une page Race) repartent à froid. Aucun TTL.
- **Cold start Render** : après une période d'inactivité, la première
  requête réveille le service (~30 s). Le cache ne règle pas ça — voir
  plus bas.

## Ce que fait le kit (3 couches)

1. **Cache mémoire front** (`frontend/src/api/client.ts`, fichier complet)
   - Les réponses GET réussies sont gardées **5 minutes** en mémoire :
     retour en arrière = affichage instantané, zéro réseau.
   - Les requêtes identiques simultanées sont **dédupliquées** (une seule
     part sur le réseau).
   - `clearApiCache()` est appelé après une synchro réussie
     (`SyncButton.tsx`, fichier complet) pour ne pas servir les données
     d'avant la synchro.

2. **Cache BigQuery élargi + purgé au bon moment** (`backend-cache.patch`)
   - `lru_cache` : **64 → 512** entrées (`utils/utils_gcp.py`).
   - Après une synchro in-app réussie, le scheduler appelle
     `query_bigquery.cache_clear()` (`api/sync_scheduler.py`) : avant,
     les anciens résultats restaient servis jusqu'à éviction.

3. **En-têtes Cache-Control** (`backend-cache.patch`, `api/main.py`)
   - Les GET `/api/*` (hors sync/status/download) renvoient
     `private, max-age=300, stale-while-revalidate=600` : le navigateur
     réutilise aussi les réponses après un rechargement complet de page.

## Installation

- Copie `frontend/src/api/client.ts` et `frontend/src/components/SyncButton.tsx`.
- `git apply backend-cache.patch` (3 fichiers back, préparé contre `ea94f07`).
- Vérifié : `npm run build` OK, `py_compile` OK.

## Ce que ça change en pratique

- Navigation entre onglets et retours en arrière : **instantanés**
  pendant 5 minutes, puis au pire un aller-retour vers un backend dont
  le cache BigQuery est chaud (pas de requête BigQuery).
- Page Race Cozumel revisitée : avant = ~10 requêtes BigQuery possibles
  à froid ; après = cache front, sinon cache back.

## Limite honnête

Le **premier** chargement après l'endormissement de Render reste lent
(c'est le réveil du service, pas les données). Solutions possibles si ça
te gêne : instance Render non-free, ou un ping externe périodique —
à décider séparément.
