/**
 * Consola Administrativa y de Observabilidad Web Soberana (Puerto 3000)
 * Servidor HTTP Autocontenido - Cero Dependencias Externas (FOSS)
 * Hackathon Venezuela Innova 2026
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');
const crypto = require('crypto');

const PORT = process.env.PORT || 3000;
const BACKEND_URL = process.env.BACKEND_URL || 'http://backend-nucleo:8000';
const PUBLIC_DIR = path.join(__dirname, 'public');

// Estado local simulado (para modo desacoplado / offline / testing)
const mockState = {
  sites: [
    {
      site_id: 'default',
      domain: 'tramites.gob.ve',
      site_key: 'vh_site_9f8e7d6c5b4a3210',
      secret_key: 'vh_sec_1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d',
      policy: {
        mode: 'challenge',
        ai_thresholds: {
          challenge_min: 0.35,
          block_min: 0.75
        },
        protected_routes: [
          { path_prefix: '/login', methods: ['POST'], require_token: true, rate_limit_rpm: 10 },
          { path_prefix: '/api/consulta', methods: ['GET', 'POST'], require_token: true, rate_limit_rpm: 30 }
        ],
        rate_limit_global_rpm: 120,
        ip_whitelist: ['127.0.0.1', '10.0.0.0/8'],
        ip_blacklist: ['198.51.100.42']
      }
    }
  ],
  cryptoKeys: [
    {
      kid: 'key-2026-01',
      algorithm: 'EdDSA',
      curve: 'Ed25519',
      active: true,
      created_at: '2026-11-20T08:00:00Z',
      public_key_pem: '-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEANkP8h3Qy8vL9Vn7vT7sZ3A1rQ8bN4p6vL2mK0jH9fGs=\n-----END PUBLIC KEY-----'
    }
  ],
  aiModel: {
    version: 'lgbm-conductual-v1.0.0',
    accuracy: 0.984,
    avg_inference_ms: 3.8,
    p99_inference_ms: 11.2,
    loaded_at: '2026-11-26T00:00:00Z',
    status: 'active'
  },
  auditLogs: [
    {
      id: 1,
      timestamp: '2026-11-26T14:00:00Z',
      actor_username: 'admin_seguridad',
      actor_role: 'security_admin',
      action: 'SYSTEM_BOOT',
      resource: 'consola-admin',
      prev_hash: '0000000000000000000000000000000000000000000000000000000000000000',
      entry_hash: 'a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0'
    },
    {
      id: 2,
      timestamp: '2026-11-26T15:15:00Z',
      actor_username: 'operador_gob',
      actor_role: 'operator',
      action: 'POLICY_MODE_CHANGED',
      resource: 'site:default',
      prev_hash: 'a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0',
      entry_hash: 'b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef01'
    },
    {
      id: 3,
      timestamp: '2026-11-26T18:15:00Z',
      actor_username: 'admin_seguridad',
      actor_role: 'security_admin',
      action: 'CRYPTO_KEY_ROTATED',
      resource: 'kid:key-2026-01',
      prev_hash: 'b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef01',
      entry_hash: '0000e8d2c1a7428f95c478a5e7834219b16542ef9c812d45a9071bce8974a123'
    }
  ]
};

// Generador de hashes encadenados para la auditoría inmutable
function appendAuditLog(username, role, action, resource) {
  const last = mockState.auditLogs[mockState.auditLogs.length - 1];
  const prevHash = last ? last.entry_hash : '0'.repeat(64);
  const now = new Date().toISOString();
  const id = (last ? last.id : 0) + 1;
  const payload = `${prevHash}|${id}|${now}|${username}|${role}|${action}|${resource}`;
  const entryHash = crypto.createHash('sha256').update(payload).digest('hex');

  const logEntry = {
    id,
    timestamp: now,
    actor_username: username,
    actor_role: role,
    action,
    resource,
    prev_hash: prevHash,
    entry_hash: entryHash
  };

  mockState.auditLogs.push(logEntry);
  return logEntry;
}

// MIME types estáticos
const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon'
};

const server = http.createServer((req, res) => {
  const parsedUrl = url.parse(req.url, true);
  const pathname = parsedUrl.pathname;

  // Habilitar CORS para integración interna
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Human-Token');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  // --- Endpoints de API Local / Mock para la Consola ---
  if (pathname.startsWith('/api/v1/')) {
    handleApiRequest(pathname, req, res);
    return;
  }

  // --- Servidor de Archivos Estáticos ---
  let filePath = path.join(PUBLIC_DIR, pathname === '/' ? 'index.html' : pathname);

  // Seguridad: evitar directory traversal
  if (!filePath.startsWith(PUBLIC_DIR)) {
    res.writeHead(403, { 'Content-Type': 'text/plain' });
    res.end('Acceso Prohibido');
    return;
  }

  fs.stat(filePath, (err, stats) => {
    if (err || !stats.isFile()) {
      // Fallback a index.html para SPA
      filePath = path.join(PUBLIC_DIR, 'index.html');
    }

    const ext = path.extname(filePath).toLowerCase();
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';

    fs.readFile(filePath, (readErr, content) => {
      if (readErr) {
        res.writeHead(500, { 'Content-Type': 'text/plain' });
        res.end('Error interno al servir archivo');
      } else {
        res.writeHead(200, {
          'Content-Type': contentType,
          'X-Content-Type-Options': 'nosniff',
          'X-Frame-Options': 'DENY'
        });
        res.end(content);
      }
    });
  });
});

function handleApiRequest(pathname, req, res) {
  let body = '';
  req.on('data', chunk => { body += chunk; });
  req.on('end', () => {
    let parsedBody = {};
    if (body) {
      try { parsedBody = JSON.parse(body); } catch (e) { }
    }

    // 1. Observabilidad en Tiempo Real (Contrato 4.1)
    if (pathname === '/api/v1/admin/observability/summary') {
      const now = new Date();
      const summary = {
        window: 'last_60_minutes',
        traffic_stats: {
          total_requests: 14820 + Math.floor(Math.random() * 40),
          verified_humans: 11210 + Math.floor(Math.random() * 25),
          interactive_challenges_solved: 980 + Math.floor(Math.random() * 5),
          bots_blocked: 2410 + Math.floor(Math.random() * 10),
          ddos_rate_limited: 220 + Math.floor(Math.random() * 2),
          human_percentage: 82.25
        },
        ai_performance: {
          active_model_version: mockState.aiModel.version,
          avg_inference_ms: parseFloat((3.6 + Math.random() * 0.4).toFixed(1)),
          p99_inference_ms: parseFloat((10.8 + Math.random() * 0.8).toFixed(1)),
          model_accuracy: mockState.aiModel.accuracy
        },
        recent_security_events: [
          {
            event_id: 'evt_' + Date.now().toString(36),
            timestamp: now.toISOString(),
            ip_hash: 'sha256:' + crypto.createHash('sha256').update(now.toISOString()).digest('hex').substring(0, 16) + '...',
            route: '/login',
            action: 'blocked',
            reason: 'high_bot_risk_score',
            risk_score: 0.94
          },
          {
            event_id: 'evt_002',
            timestamp: new Date(Date.now() - 65000).toISOString(),
            ip_hash: 'sha256:4a8b7c6d5e1f...',
            route: '/api/consulta',
            action: 'rate_limited',
            reason: 'rpm_threshold_exceeded',
            risk_score: 0.82
          },
          {
            event_id: 'evt_003',
            timestamp: new Date(Date.now() - 130000).toISOString(),
            ip_hash: 'sha256:9f86d081884c...',
            route: '/login',
            action: 'challenge_solved',
            reason: 'spatial_alignment_verified',
            risk_score: 0.38
          }
        ]
      };
      sendJson(res, 200, summary);
      return;
    }

    // 2. Auditoría Inmutable (Contrato 4.2)
    if (pathname === '/api/v1/admin/audit-logs') {
      sendJson(res, 200, {
        chain_integrity_valid: true,
        items: mockState.auditLogs.slice().reverse()
      });
      return;
    }

    // 3. Gestión de Sitios y Políticas (Módulos 1 y 2)
    if (pathname === '/api/v1/admin/sites' || pathname === '/api/v1/policies/default') {
      if (req.method === 'GET') {
        const site = mockState.sites[0];
        sendJson(res, 200, {
          site_id: site.site_id,
          site_key: site.site_key,
          secret_key: site.secret_key,
          updated_at: new Date().toISOString(),
          policy: site.policy,
          crypto_public_keys: mockState.cryptoKeys
        });
        return;
      }
      if (req.method === 'POST' || req.method === 'PUT') {
        if (parsedBody.policy) {
          mockState.sites[0].policy = Object.assign({}, mockState.sites[0].policy, parsedBody.policy);
        }
        appendAuditLog('operador_consola', 'operator', 'POLICY_UPDATED', 'site:default');
        sendJson(res, 200, { status: 'success', message: 'Política actualizada exitosamente', policy: mockState.sites[0].policy });
        return;
      }
    }

    // 4. Bóveda Criptográfica (Módulo 3)
    if (pathname === '/api/v1/admin/crypto/keys') {
      sendJson(res, 200, { keys: mockState.cryptoKeys });
      return;
    }

    if (pathname === '/api/v1/admin/crypto/rotate' && req.method === 'POST') {
      const newKid = 'key-2026-' + String(mockState.cryptoKeys.length + 1).padStart(2, '0');
      // Generación local de par Ed25519 con crypto estándar de Node
      try {
        const { publicKey } = crypto.generateKeyPairSync('ed25519');
        const pem = publicKey.export({ type: 'spki', format: 'pem' });
        mockState.cryptoKeys.forEach(k => { k.active = false; });
        mockState.cryptoKeys.push({
          kid: newKid,
          algorithm: 'EdDSA',
          curve: 'Ed25519',
          active: true,
          created_at: new Date().toISOString(),
          public_key_pem: pem
        });
      } catch (e) {
        // Fallback PEM si ed25519 no está disponible en entorno limitado
        mockState.cryptoKeys.forEach(k => { k.active = false; });
        mockState.cryptoKeys.push({
          kid: newKid,
          algorithm: 'EdDSA',
          curve: 'Ed25519',
          active: true,
          created_at: new Date().toISOString(),
          public_key_pem: '-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEA' + crypto.randomBytes(32).toString('base64') + '\n-----END PUBLIC KEY-----'
        });
      }

      appendAuditLog('admin_seguridad', 'security_admin', 'CRYPTO_KEY_ROTATED', 'kid:' + newKid);
      sendJson(res, 200, { status: 'success', message: 'Clave Ed25519 rotada exitosamente', active_key: mockState.cryptoKeys[mockState.cryptoKeys.length - 1] });
      return;
    }

    // 5. Gestión del Modelo de IA (Módulo 5)
    if (pathname === '/api/v1/admin/model' && req.method === 'GET') {
      sendJson(res, 200, mockState.aiModel);
      return;
    }

    if (pathname === '/api/v1/admin/model/upload' && req.method === 'POST') {
      const filename = parsedBody.filename || 'modelo_conductual_actualizado.onnx';
      const version = 'lgbm-conductual-v' + (Date.now().toString().slice(-4));
      mockState.aiModel.version = version;
      mockState.aiModel.loaded_at = new Date().toISOString();
      mockState.aiModel.accuracy = 0.988;

      appendAuditLog('admin_seguridad', 'security_admin', 'AI_MODEL_RELOADED', filename + ' (' + version + ')');
      sendJson(res, 200, {
        status: 'success',
        message: 'Modelo ONNX cargado e intercambiado en caliente satisfactoriamente',
        ai_model: mockState.aiModel
      });
      return;
    }

    // 6. Login y Verificación MFA/TOTP
    if (pathname === '/api/v1/admin/auth/login' && req.method === 'POST') {
      const { username, password, totp_code } = parsedBody;
      let role = 'auditor';
      if (username === 'admin') role = 'security_admin';
      else if (username === 'operador') role = 'operator';

      // Validación estricta de MFA/TOTP (Código predeterminado de demostración: 123456)
      const totpValid = (totp_code === '123456');
      if (totpValid) {
        appendAuditLog(username || 'admin', role, 'USER_LOGIN_SUCCESS', 'consola-admin');
        sendJson(res, 200, {
          authenticated: true,
          username: username || 'admin',
          role: role,
          token: 'vh_admin_jwt_' + crypto.randomBytes(16).toString('hex')
        });
      } else {
        sendJson(res, 401, {
          error: {
            code: 'INVALID_MFA_TOKEN',
            message: 'Código de segundo factor MFA/TOTP inválido (Use 123456 en prueba).',
            trace_id: crypto.randomUUID(),
            timestamp: new Date().toISOString()
          }
        });
      }
      return;
    }

    // Ruta no encontrada
    sendJson(res, 404, {
      error: {
        code: 'NOT_FOUND',
        message: 'Ruta no encontrada en la API administrativa.',
        trace_id: crypto.randomUUID(),
        timestamp: new Date().toISOString()
      }
    });
  });
}

function sendJson(res, statusCode, data) {
  res.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
    'X-Content-Type-Options': 'nosniff'
  });
  res.end(JSON.stringify(data, null, 2));
}

server.listen(PORT, '0.0.0.0', () => {
  console.log(`=======================================================`);
  console.log(` Consola Administrativa Soberana (Venezuela Innova 2026)`);
  console.log(` Servidor activo en: http://0.0.0.0:${PORT}`);
  console.log(` Cero dependencias externas • 100% On-Premise (FOSS)`);
  console.log(`=======================================================`);
});
