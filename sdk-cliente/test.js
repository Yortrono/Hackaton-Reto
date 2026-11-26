const assert = require('assert');
const fs = require('fs');
const path = require('path');

console.log('--- Iniciando Pruebas Unitarias del SDK Cliente ---');

// 1. Verificar existencia de archivos esenciales
assert(fs.existsSync(path.join(__dirname, 'sdk-verificacion.js')), 'sdk-verificacion.js debe existir');
assert(fs.existsSync(path.join(__dirname, 'sdk-verificacion.min.js')), 'sdk-verificacion.min.js debe existir');
assert(fs.existsSync(path.join(__dirname, 'index.html')), 'index.html debe existir');

// 2. Cargar SDK en entorno simulado
global.window = {
  location: { pathname: '/login' },
  addEventListener: () => {},
  removeEventListener: () => {},
  screen: { width: 1920, height: 1080 },
  innerWidth: 1280,
  innerHeight: 720
};
global.navigator = {
  userAgent: 'Mozilla/5.0 Test Suite Linux',
  webdriver: false,
  plugins: [1, 2, 3],
  language: 'es-VE',
  languages: ['es-VE', 'es', 'en']
};
global.document = {
  currentScript: null,
  addEventListener: () => {},
  querySelectorAll: () => [],
  getElementById: () => null
};

const VerificacionHumana = require('./sdk-verificacion.js');

assert(typeof VerificacionHumana === 'object', 'VerificacionHumana debe exportarse correctamente');
assert(typeof VerificacionHumana.init === 'function', 'init debe ser una función');
assert(typeof VerificacionHumana.TelemetryCollector === 'function', 'TelemetryCollector debe ser una función');

// 3. Probar cálculo de telemetría y contrato exacto
const collector = new VerificacionHumana.TelemetryCollector();
// Simular eventos
collector.onPointerMove({ clientX: 100, clientY: 100 });
collector.onPointerMove({ clientX: 120, clientY: 110 });
collector.onPointerMove({ clientX: 150, clientY: 130 });
collector.onKeyDown({});
collector.onKeyUp({});

const telemetry = collector.computeMetrics('test-challenge-uuid');

// Validar llaves requeridas por el contrato JSON 2.2
assert.strictEqual(telemetry.challenge_id, 'test-challenge-uuid');
assert(typeof telemetry.telemetry_window_ms === 'number');

assert(typeof telemetry.pointer_metrics === 'object');
assert(typeof telemetry.pointer_metrics.event_count === 'number');
assert(typeof telemetry.pointer_metrics.mean_velocity === 'number');
assert(typeof telemetry.pointer_metrics.std_acceleration === 'number');
assert(typeof telemetry.pointer_metrics.angular_entropy === 'number');
assert(typeof telemetry.pointer_metrics.straight_line_ratio === 'number');

assert(typeof telemetry.keyboard_metrics === 'object');
assert(typeof telemetry.keyboard_metrics.key_count === 'number');
assert(typeof telemetry.keyboard_metrics.mean_dwell_ms === 'number');
assert(typeof telemetry.keyboard_metrics.std_flight_ms === 'number');

assert(typeof telemetry.environment_signals === 'object');
assert.strictEqual(telemetry.environment_signals.webdriver_flag, false);
assert.strictEqual(typeof telemetry.environment_signals.plugins_count, 'number');
assert.strictEqual(telemetry.environment_signals.languages_consistent, true);
assert.strictEqual(telemetry.environment_signals.viewport_ratio_valid, true);
assert(typeof telemetry.environment_signals.time_to_first_interaction_ms === 'number');

console.log('✓ Contrato de telemetría verificado al 100%');
console.log('✓ Pruebas del SDK Cliente superadas con éxito.');
