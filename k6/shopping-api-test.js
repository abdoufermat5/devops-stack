// ============================================================
// SCRIPT K6 — Shopping List API
// Teste les vrais endpoints de ton app FastAPI
// ============================================================
// k6 run shopping-api-test.js
// ============================================================

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// ------------------------------------------------------------
// MÉTRIQUES CUSTOM par endpoint
// On veut savoir si /products (GET) est plus lent que /products (POST)
// ------------------------------------------------------------
const createTrend  = new Trend('duration_create_product',  true);
const listTrend    = new Trend('duration_list_products',   true);
const deleteTrend  = new Trend('duration_delete_product',  true);
const erreurRate   = new Rate('erreurs');

// ------------------------------------------------------------
// OPTIONS
// ------------------------------------------------------------
export const options = {
  stages: [
    { duration: '10s', target: 5  },  // warm-up léger
    { duration: '20s', target: 20 },  // charge normale
    { duration: '20s', target: 50 },  // pic de charge
    { duration: '10s', target: 0  },  // descente
  ],
  thresholds: {
    // L'API doit répondre en moins de 500ms au p95 sur tous les endpoints
    http_req_duration:       ['p(95)<500'],
    // Les créations de produit spécifiquement doivent rester sous 600ms
    duration_create_product: ['p(95)<600'],
    // Moins de 1% d'erreurs tolérées
    http_req_failed:         ['rate<0.01'],
    erreurs:                 ['rate<0.01'],
  },
};

// ------------------------------------------------------------
// SETUP
// Vérifie que l'API est accessible avant de démarrer le test.
// Si elle ne répond pas, on arrête tout plutôt que de lancer
// 50 VUs sur une app morte.
// ------------------------------------------------------------
export function setup() {
  const res = http.get('http://localhost:30800/');
  if (res.status !== 200) {
    throw new Error(`L'API ne répond pas. Status: ${res.status}`);
  }
  console.log('API accessible, démarrage du test...');
  return {};
}

// ------------------------------------------------------------
// SCÉNARIO PRINCIPAL
// Simule un utilisateur qui :
//   1. Liste les produits existants
//   2. Crée un nouveau produit
//   3. Récupère ce produit par son ID
//   4. Marque le produit comme acheté
//   5. Supprime le produit (nettoyage)
// ------------------------------------------------------------
export default function () {
  const BASE = 'http://localhost:30800';

  // Headers communs à toutes les requêtes
  const headers = { 'Content-Type': 'application/json' };

  // ---- 1. Lister les produits ----
  group('GET /products', function () {
    const start = Date.now();
    const res = http.get(`${BASE}/products`, { headers });

    listTrend.add(Date.now() - start);
    erreurRate.add(res.status !== 200);

    check(res, {
      'liste retourne 200':        (r) => r.status === 200,
      'réponse est un tableau':    (r) => Array.isArray(r.json()),
    });
  });

  sleep(0.3);

  // ---- 2. Créer un produit ----
  // On génère un nom unique pour éviter les conflits entre VUs
  let productId = null;

  group('POST /products', function () {
    const payload = JSON.stringify({
      name:     `Produit-${__VU}-${__ITER}`,   // __VU = ID du VU, __ITER = numéro d'itération
      category: 'fruits',
      quantity: Math.floor(Math.random() * 5) + 1,
    });

    const start = Date.now();
    const res = http.post(`${BASE}/products`, payload, { headers });

    createTrend.add(Date.now() - start);
    erreurRate.add(res.status !== 201);

    check(res, {
      'création retourne 201':     (r) => r.status === 201,
      'réponse contient un id':    (r) => r.json('id') !== undefined,
    });

    // On récupère l'ID pour les étapes suivantes
    if (res.status === 201) {
      productId = res.json('id');
    }
  });

  sleep(0.2);

  // ---- 3. Récupérer le produit créé ----
  if (productId !== null) {
    group('GET /products/:id', function () {
      const res = http.get(`${BASE}/products/${productId}`, { headers });

      check(res, {
        'get par id retourne 200':    (r) => r.status === 200,
        "l'id correspond":            (r) => r.json('id') === productId,
      });
    });

    sleep(0.2);

    // ---- 4. Marquer comme acheté (PATCH) ----
    group('PATCH /products/:id', function () {
      const payload = JSON.stringify({ bought: true });
      const res = http.patch(`${BASE}/products/${productId}`, payload, { headers });

      check(res, {
        'patch retourne 200': (r) => r.status === 200,
      });
    });

    sleep(0.2);

    // ---- 5. Supprimer le produit (nettoyage) ----
    // Important : sans nettoyage, la DB grossit indéfiniment pendant le test
    group('DELETE /products/:id', function () {
      const start = Date.now();
      const res = http.del(`${BASE}/products/${productId}`, null, { headers });

      deleteTrend.add(Date.now() - start);

      check(res, {
        'delete retourne 204': (r) => r.status === 204,
      });
    });
  }

  // Pause finale — simule le temps de réflexion d'un utilisateur réel
  sleep(0.5);
}

// ------------------------------------------------------------
// TEARDOWN
// ------------------------------------------------------------
export function teardown() {
  console.log('Test terminé — vérifie les dashboards Grafana !');
}
