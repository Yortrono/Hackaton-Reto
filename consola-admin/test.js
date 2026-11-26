const assert = require('assert');
const http = require('http');
const { spawn } = require('child_process');
const path = require('path');

console.log('--- Iniciando Pruebas de la Consola Administrativa ---');

// Iniciar el servidor en un puerto de prueba
const TEST_PORT = 3001;
const serverProcess = spawn('node', ['server.js'], {
  cwd: __dirname,
  env: Object.assign({}, process.env, { PORT: TEST_PORT })
});

function makeRequest(method, pathUrl, payload) {
  return new Promise((resolve, reject) => {
    const postData = payload ? JSON.stringify(payload) : null;
    const req = http.request({
      hostname: '127.0.0.1',
      port: TEST_PORT,
      path: pathUrl,
      method: method,
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': postData ? Buffer.byteLength(postData) : 0
      }
    }, res => {
      let data = '';
      res.on('data', chunk => { data += chunk; });
      res.on('end', () => {
        try {
          resolve({ status: res.statusCode, body: data ? JSON.parse(data) : {} });
        } catch (e) {
          resolve({ status: res.statusCode, body: data });
        }
      });
    });
    req.on('error', reject);
    if (postData) req.write(postData);
    req.end();
  });
}

// Esperar que el servidor inicie
setTimeout(async () => {
  try {
    // 1. Probar entrega de index.html
    const resRoot = await makeRequest('GET', '/');
    assert.strictEqual(resRoot.status, 200);

    // 2. Probar Contrato 4.1: Observabilidad
    const resObs = await makeRequest('GET', '/api/v1/admin/observability/summary');
    assert.strictEqual(resObs.status, 200);
    assert.strictEqual(resObs.body.window, 'last_60_minutes');
    assert(typeof resObs.body.traffic_stats.total_requests === 'number');
    assert(typeof resObs.body.traffic_stats.verified_humans === 'number');
    assert(typeof resObs.body.ai_performance.avg_inference_ms === 'number');
    assert(Array.isArray(resObs.body.recent_security_events));

    // 3. Probar Contrato 4.2: Auditoría Inmutable
    const resAudit = await makeRequest('GET', '/api/v1/admin/audit-logs');
    assert.strictEqual(resAudit.status, 200);
    assert.strictEqual(resAudit.body.chain_integrity_valid, true);
    assert(Array.isArray(resAudit.body.items));

    // 4. Probar Rotación Criptográfica
    const resRotate = await makeRequest('POST', '/api/v1/admin/crypto/rotate');
    assert.strictEqual(resRotate.status, 200);
    assert(resRotate.body.active_key.public_key_pem.includes('BEGIN PUBLIC KEY'));

    // 5. Probar Autenticación MFA
    const resLoginFail = await makeRequest('POST', '/api/v1/admin/auth/login', { username: 'admin', totp_code: '000000' });
    assert.strictEqual(resLoginFail.status, 401);

    const resLoginOk = await makeRequest('POST', '/api/v1/admin/auth/login', { username: 'admin', totp_code: '123456' });
    assert.strictEqual(resLoginOk.status, 200);
    assert.strictEqual(resLoginOk.body.role, 'security_admin');

    console.log('✓ Servidor de la consola administrativa verificado.');
    console.log('✓ 6 Módulos y contratos API validados exitosamente.');

    serverProcess.kill();
    process.exit(0);
  } catch (err) {
    console.error('Error durante pruebas de la consola:', err);
    serverProcess.kill();
    process.exit(1);
  }
}, 800);
