/**
 * Servicio Autónomo de Verificación Humana y Mitigación de Bots (Venezuela Innova 2026)
 * SDK Cliente Minimalista Autocontenido - Cero Dependencias Externas (FOSS)
 * 
 * Privacidad por Diseño:
 * - Toda la telemetría conductual se calcula de forma agregada en memoria RAM.
 * - NUNCA se transmiten coordenadas (x,y) crudas ni texto pulsado en teclado.
 * - Compatible con modo offline / on-premise estricto (cero llamadas a CDNs).
 */
(function (global) {
  'use strict';

  // Configuración predeterminada
  var DEFAULT_CONFIG = {
    apiBase: '',
    siteKey: '',
    targetRoute: window.location.pathname || '/',
    containerId: 'verificacion-humana-widget',
    autoInit: true,
    passiveDelayMs: 1200,
    onVerified: null,
    onChallengeRequired: null,
    onError: null
  };

  /**
   * Colector de Telemetría Efímera en Memoria
   */
  function TelemetryCollector() {
    this.startTime = Date.now();
    this.timeToFirstInteraction = null;

    // Buffer de puntero (en memoria, no se almacena en disco ni se envía crudo)
    this.pointerEvents = [];
    this.maxPointerSamples = 80;

    // Métricas de teclado agregadas
    this.keyPresses = [];
    this.keyCount = 0;
    this.lastKeyReleaseTime = null;
    this.flightTimes = [];
    this.dwellTimes = [];

    this._boundOnPointer = this.onPointerMove.bind(this);
    this._boundOnKeyDown = this.onKeyDown.bind(this);
    this._boundOnKeyUp = this.onKeyUp.bind(this);

    this.attach();
  }

  TelemetryCollector.prototype.attach = function () {
    if (typeof window === 'undefined') return;
    window.addEventListener('pointermove', this._boundOnPointer, { passive: true });
    window.addEventListener('mousemove', this._boundOnPointer, { passive: true });
    window.addEventListener('keydown', this._boundOnKeyDown, { passive: true });
    window.addEventListener('keyup', this._boundOnKeyUp, { passive: true });
  };

  TelemetryCollector.prototype.detach = function () {
    if (typeof window === 'undefined') return;
    window.removeEventListener('pointermove', this._boundOnPointer);
    window.removeEventListener('mousemove', this._boundOnPointer);
    window.removeEventListener('keydown', this._boundOnKeyDown);
    window.removeEventListener('keyup', this._boundOnKeyUp);
  };

  TelemetryCollector.prototype.markFirstInteraction = function () {
    if (this.timeToFirstInteraction === null) {
      this.timeToFirstInteraction = Math.max(1, Date.now() - this.startTime);
    }
  };

  TelemetryCollector.prototype.onPointerMove = function (e) {
    this.markFirstInteraction();
    var now = Date.now();
    var x = e.clientX || 0;
    var y = e.clientY || 0;

    this.pointerEvents.push({ x: x, y: y, t: now });
    if (this.pointerEvents.length > this.maxPointerSamples) {
      this.pointerEvents.shift();
    }
  };

  TelemetryCollector.prototype.onKeyDown = function (e) {
    this.markFirstInteraction();
    this.keyCount++;
    var now = Date.now();

    if (this.lastKeyReleaseTime !== null) {
      var flight = now - this.lastKeyReleaseTime;
      if (flight >= 0 && flight < 3000) {
        this.flightTimes.push(flight);
        if (this.flightTimes.length > 50) this.flightTimes.shift();
      }
    }

    // Guardar timestamp de inicio sin registrar qué tecla fue presionada (privacidad)
    this.keyPresses.push(now);
    if (this.keyPresses.length > 30) this.keyPresses.shift();
  };

  TelemetryCollector.prototype.onKeyUp = function () {
    var now = Date.now();
    this.lastKeyReleaseTime = now;
    if (this.keyPresses.length > 0) {
      var downTime = this.keyPresses.shift();
      var dwell = now - downTime;
      if (dwell >= 0 && dwell < 2000) {
        this.dwellTimes.push(dwell);
        if (this.dwellTimes.length > 50) this.dwellTimes.shift();
      }
    }
  };

  /**
   * Cálculo matemático de métricas agregadas
   */
  TelemetryCollector.prototype.computeMetrics = function (challengeId) {
    var now = Date.now();
    var windowMs = Math.max(100, now - this.startTime);

    // 1. Métricas de puntero
    var pCount = this.pointerEvents.length;
    var velocities = [];
    var accelerations = [];
    var angles = [];
    var totalPath = 0;

    for (var i = 1; i < pCount; i++) {
      var p0 = this.pointerEvents[i - 1];
      var p1 = this.pointerEvents[i];
      var dt = (p1.t - p0.t) || 1;
      var dx = p1.x - p0.x;
      var dy = p1.y - p0.y;
      var dist = Math.sqrt(dx * dx + dy * dy);
      totalPath += dist;

      var vel = dist / dt; // px/ms
      velocities.push(vel);

      var angle = Math.atan2(dy, dx);
      angles.push(angle);
    }

    for (var j = 1; j < velocities.length; j++) {
      var dv = velocities[j] - velocities[j - 1];
      var pPrev = this.pointerEvents[j];
      var pCurr = this.pointerEvents[j + 1];
      var dtAcc = (pCurr.t - pPrev.t) || 1;
      accelerations.push(Math.abs(dv / dtAcc));
    }

    var meanVelocity = velocities.length > 0
      ? (velocities.reduce(function (a, b) { return a + b; }, 0) / velocities.length)
      : 0.0;

    var meanAcc = accelerations.length > 0
      ? (accelerations.reduce(function (a, b) { return a + b; }, 0) / accelerations.length)
      : 0.0;

    var stdAcceleration = 0.0;
    if (accelerations.length > 1) {
      var sumSquares = accelerations.reduce(function (acc, val) {
        return acc + Math.pow(val - meanAcc, 2);
      }, 0);
      stdAcceleration = Math.sqrt(sumSquares / accelerations.length);
    }

    // Entropía angular (histograma de 8 cuadrantes de dirección)
    var octants = [0, 0, 0, 0, 0, 0, 0, 0];
    for (var a = 0; a < angles.length; a++) {
      var normAngle = angles[a];
      if (normAngle < 0) normAngle += 2 * Math.PI;
      var oct = Math.floor((normAngle / (2 * Math.PI)) * 8) % 8;
      octants[oct]++;
    }

    var angularEntropy = 0.0;
    if (angles.length > 0) {
      for (var o = 0; o < 8; o++) {
        var p = octants[o] / angles.length;
        if (p > 0) {
          angularEntropy -= p * (Math.log(p) / Math.LN2);
        }
      }
    }

    // Straight line ratio (distancia neta / distancia total recorrida)
    var straightLineRatio = 0.0;
    if (pCount > 1 && totalPath > 0) {
      var firstP = this.pointerEvents[0];
      var lastP = this.pointerEvents[pCount - 1];
      var netDx = lastP.x - firstP.x;
      var netDy = lastP.y - firstP.y;
      var netDist = Math.sqrt(netDx * netDx + netDy * netDy);
      straightLineRatio = Math.min(1.0, netDist / totalPath);
    }

    // 2. Métricas de teclado
    var meanDwell = this.dwellTimes.length > 0
      ? (this.dwellTimes.reduce(function (a, b) { return a + b; }, 0) / this.dwellTimes.length)
      : 0.0;

    var stdFlight = 0.0;
    if (this.flightTimes.length > 1) {
      var meanFlight = this.flightTimes.reduce(function (a, b) { return a + b; }, 0) / this.flightTimes.length;
      var sqFlight = this.flightTimes.reduce(function (acc, val) {
        return acc + Math.pow(val - meanFlight, 2);
      }, 0);
      stdFlight = Math.sqrt(sqFlight / this.flightTimes.length);
    }

    // 3. Señales de entorno del navegador
    var hasNavigator = typeof navigator !== 'undefined';
    var webdriverFlag = hasNavigator ? Boolean(navigator.webdriver) : false;
    var pluginsCount = (hasNavigator && navigator.plugins) ? navigator.plugins.length : 0;
    var languagesConsistent = hasNavigator
      ? Boolean(navigator.language && Array.isArray(navigator.languages) && navigator.languages.indexOf(navigator.language) !== -1)
      : true;
    var screenWidth = (typeof screen !== 'undefined' && screen.width) ? screen.width : ((typeof window !== 'undefined' && window.screen && window.screen.width) ? window.screen.width : 1920);
    var viewportValid = typeof window !== 'undefined'
      ? Boolean(window.innerWidth > 0 && window.innerHeight > 0 && screenWidth >= window.innerWidth)
      : true;

    return {
      challenge_id: challengeId,
      telemetry_window_ms: windowMs,
      pointer_metrics: {
        event_count: pCount,
        mean_velocity: parseFloat(meanVelocity.toFixed(2)),
        std_acceleration: parseFloat(stdAcceleration.toFixed(2)),
        angular_entropy: parseFloat(angularEntropy.toFixed(2)),
        straight_line_ratio: parseFloat(straightLineRatio.toFixed(2))
      },
      keyboard_metrics: {
        key_count: this.keyCount,
        mean_dwell_ms: parseFloat(meanDwell.toFixed(1)),
        std_flight_ms: parseFloat(stdFlight.toFixed(1))
      },
      environment_signals: {
        webdriver_flag: webdriverFlag,
        plugins_count: pluginsCount,
        languages_consistent: languagesConsistent,
        viewport_ratio_valid: viewportValid,
        time_to_first_interaction_ms: this.timeToFirstInteraction || 0
      }
    };
  };

  /**
   * Resuelve el Proof of Work ligero con Web Crypto SHA-256
   */
  function solvePoW(nonce, difficulty) {
    var prefix = '0'.repeat(difficulty || 3);
    var encoder = new TextEncoder();

    function tryIteration(counter) {
      var hexCounter = counter.toString(16);
      var text = nonce + hexCounter;
      var data = encoder.encode(text);

      return crypto.subtle.digest('SHA-256', data).then(function (buf) {
        var byteArray = new Uint8Array(buf);
        var hexHash = '';
        for (var i = 0; i < 4; i++) {
          var h = byteArray[i].toString(16);
          if (h.length < 2) h = '0' + h;
          hexHash += h;
        }

        if (hexHash.substring(0, difficulty) === prefix) {
          return hexCounter;
        }

        if (counter > 200000) {
          throw new Error('POW_COMPUTATION_LIMIT_EXCEEDED');
        }

        return tryIteration(counter + 1);
      });
    }

    if (typeof crypto !== 'undefined' && crypto.subtle) {
      return tryIteration(0);
    } else {
      return Promise.reject(new Error('WEB_CRYPTO_UNAVAILABLE'));
    }
  }

  /**
   * Gestor Principal del SDK
   */
  function VerificacionHumanaSDK(userConfig) {
    this.config = Object.assign({}, DEFAULT_CONFIG, userConfig || {});
    this.telemetry = new TelemetryCollector();
    this.activeChallenge = null;
    this.verifiedToken = null;
    this.initResponse = null;

    if (this.config.autoInit) {
      var self = this;
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
          self.iniciar();
        });
      } else {
        setTimeout(function () {
          self.iniciar();
        }, 100);
      }
    }
  }

  /**
   * Inicia el flujo: Llamada a /api/v1/challenge/init y verificación pasiva
   */
  VerificacionHumanaSDK.prototype.iniciar = function () {
    var self = this;
    var base = this.config.apiBase || '';
    var initUrl = base + '/api/v1/challenge/init';

    var clientContext = {
      sdk_version: '1.0.0',
      user_agent_hash: self.hashSimple(navigator.userAgent || 'unknown'),
      timezone_offset: new Date().getTimezoneOffset(),
      screen_resolution: (window.screen.width || 1920) + 'x' + (window.screen.height || 1080),
      language: navigator.language || 'es-VE'
    };

    var payload = {
      site_key: self.config.siteKey || 'vh_site_9f8e7d6c5b4a3210',
      target_route: self.config.targetRoute || window.location.pathname,
      client_context: clientContext
    };

    fetch(initUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
      body: JSON.stringify(payload)
    })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (data) {
        self.initResponse = data;
        self.activeChallenge = data;

        if (data.interactive_challenge && data.interactive_challenge.required_immediately) {
          self.renderizarDesafio(data.interactive_challenge);
        } else {
          // Espera interacción natural o ventana pasiva adaptativa
          self.programarVerificacionPasiva();
        }
      })
      .catch(function (err) {
        console.error('[VerificacionHumana] Error al conectar con el servicio soberano de desafío:', err.message);
        var container = document.getElementById(self.config.containerId);
        if (container) {
          container.innerHTML = '<div style="color: #ef4444; font-size: 13px; padding: 10px;">✕ Error de conexión con el servicio de verificación soberana.</div>';
        }
        if (typeof self.config.onError === 'function') {
          self.config.onError({ error: 'CHALLENGE_INIT_FAILED', message: err.message });
        }
      });
  };

  /**
   * Programa la verificación pasiva escuchando interacciones naturales (puntero/teclas)
   */
  VerificacionHumanaSDK.prototype.programarVerificacionPasiva = function () {
    var self = this;
    var executed = false;
    var debounceTimer = null;
    var fallbackTimer = null;

    function ejecutar() {
      if (executed) return;
      executed = true;
      limpiar();
      self.ejecutarVerificacionPasiva();
    }

    function onInteraction() {
      if (executed) return;
      if (debounceTimer) clearTimeout(debounceTimer);
      // Recolectar ~350ms de trayectoria continua antes de evaluar
      debounceTimer = setTimeout(function () {
        if (self.telemetry.pointerEvents.length >= 6 || self.telemetry.keyCount > 0) {
          ejecutar();
        }
      }, 350);
    }

    function limpiar() {
      if (typeof window === 'undefined') return;
      window.removeEventListener('pointermove', onInteraction);
      window.removeEventListener('mousemove', onInteraction);
      window.removeEventListener('keydown', onInteraction);
      window.removeEventListener('focusin', onInteraction);
      if (debounceTimer) clearTimeout(debounceTimer);
      if (fallbackTimer) clearTimeout(fallbackTimer);
    }

    if (typeof window !== 'undefined') {
      window.addEventListener('pointermove', onInteraction, { passive: true });
      window.addEventListener('mousemove', onInteraction, { passive: true });
      window.addEventListener('keydown', onInteraction, { passive: true });
      window.addEventListener('focusin', onInteraction, { passive: true });
    }

    // Si el usuario no interactúa en 3.5 segundos, evaluar automáticamente
    fallbackTimer = setTimeout(function () {
      ejecutar();
    }, 3500);
  };

  /**
   * Ejecuta la verificación pasiva con telemetría agregada y PoW
   */
  VerificacionHumanaSDK.prototype.ejecutarVerificacionPasiva = function () {
    var self = this;
    var challengeId = self.activeChallenge ? self.activeChallenge.challenge_id : self.uuidv4();
    var nonce = (self.activeChallenge && self.activeChallenge.nonce) ? self.activeChallenge.nonce : '8f14e45fceea';
    var diff = (self.activeChallenge && self.activeChallenge.pow_difficulty) ? self.activeChallenge.pow_difficulty : 3;

    solvePoW(nonce, diff).then(function (solution) {
      var telemetryData = self.telemetry.computeMetrics(challengeId);
      var verifyUrl = (self.config.apiBase || '') + '/api/v1/challenge/verify';

      var verifyPayload = {
        site_key: self.config.siteKey || 'vh_site_9f8e7d6c5b4a3210',
        challenge_id: challengeId,
        pow_solution: solution,
        telemetry: telemetryData,
        interactive_response: null
      };

      fetch(verifyUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json; charset=utf-8' },
        body: JSON.stringify(verifyPayload)
      })
        .then(function (res) {
          return res.json().then(function (json) {
            return { ok: res.ok, status: res.status, data: json };
          });
        })
        .then(function (result) {
          self.procesarResultadoVerificacion(result.data, verifyPayload);
        })
        .catch(function (err) {
          console.error('[VerificacionHumana] Error al verificar telemetría en el backend:', err.message);
          var container = document.getElementById(self.config.containerId);
          if (container) {
            container.innerHTML = '<div style="color: #ef4444; font-size: 13px; padding: 10px;">✕ Error al verificar señales conductuales en el servidor.</div>';
          }
          if (typeof self.config.onError === 'function') {
            self.config.onError({ error: 'VERIFICATION_FAILED', message: err.message });
          }
        });
    });
  };

  /**
   * Procesa la respuesta de verificación (verified, challenge_required, blocked)
   */
  VerificacionHumanaSDK.prototype.procesarResultadoVerificacion = function (data, originalPayload) {
    var self = this;
    if (data.status === 'verified' && data.jwt_token) {
      self.verifiedToken = data.jwt_token;
      self.inyectarToken(data.jwt_token);
      self.limpiarWidget();
      if (typeof self.config.onVerified === 'function') {
        self.config.onVerified(data);
      }
    } else if (data.status === 'challenge_required') {
      var challengeInfo = data.interactive_challenge || {
        type: 'spatial_alignment',
        target_angle: 135,
        tolerance: 8,
        prompt: 'Gire el anillo hasta que la marca apunte a las 4 en punto',
        accessible_hint: 'Presione las flechas izquierda o derecha para rotar y Enter para confirmar'
      };
      self.renderizarDesafio(challengeInfo, originalPayload);
      if (typeof self.config.onChallengeRequired === 'function') {
        self.config.onChallengeRequired(challengeInfo);
      }
    } else if (data.status === 'blocked') {
      self.renderizarBloqueo(data);
      if (typeof self.config.onError === 'function') {
        self.config.onError(data);
      }
    }
  };

  /**
   * Inyección transparente de Token:
   * - Cookie 'vh_token'
   * - Interceptación de fetch / XHR
   * - Inputs ocultos en formularios
   */
  VerificacionHumanaSDK.prototype.inyectarToken = function (token) {
    if (typeof document === 'undefined') return;

    // 1. Guardar en Cookie de sesión segura
    document.cookie = 'vh_token=' + encodeURIComponent(token) + '; path=/; SameSite=Lax';

    // 2. Interceptar fetch global para añadir X-Human-Token
    if (typeof window.fetch === 'function' && !window.__vh_fetch_intercepted) {
      var originalFetch = window.fetch;
      window.fetch = function (resource, init) {
        init = init || {};
        var headers = new Headers(init.headers || {});
        if (!headers.has('X-Human-Token')) {
          headers.set('X-Human-Token', token);
        }
        init.headers = headers;
        return originalFetch(resource, init);
      };
      window.__vh_fetch_intercepted = true;
    }

    // 3. Interceptar XMLHttpRequest
    if (typeof XMLHttpRequest !== 'undefined' && !XMLHttpRequest.prototype.__vh_intercepted) {
      var origOpen = XMLHttpRequest.prototype.open;
      XMLHttpRequest.prototype.open = function () {
        this.addEventListener('readystatechange', function () {
          if (this.readyState === 1) { // OPENED
            try {
              this.setRequestHeader('X-Human-Token', token);
            } catch (e) { }
          }
        });
        return origOpen.apply(this, arguments);
      };
      XMLHttpRequest.prototype.__vh_intercepted = true;
    }

    // 4. Inyectar campos ocultos en todos los formularios
    var forms = document.querySelectorAll('form');
    for (var i = 0; i < forms.length; i++) {
      var existing = forms[i].querySelector('input[name="vh_token"]');
      if (!existing) {
        var input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'vh_token';
        input.value = token;
        forms[i].appendChild(input);
      } else {
        existing.value = token;
      }
    }

    // 5. Notificación de evento personalizado
    if (typeof window.dispatchEvent === 'function') {
      var ev = new CustomEvent('verificacion-humana:verified', {
        detail: { token: token, timestamp: new Date().toISOString() }
      });
      window.dispatchEvent(ev);
    }
  };

  /**
   * Renderiza el Desafío Interactivo Accesible (spatial_alignment)
   */
  VerificacionHumanaSDK.prototype.renderizarDesafio = function (challengeInfo, originalPayload) {
    var self = this;
    var container = document.getElementById(this.config.containerId);
    if (!container) {
      container = document.createElement('div');
      container.id = this.config.containerId;
      var targetForm = document.querySelector('form') || document.body;
      if (targetForm.firstChild) {
        targetForm.insertBefore(container, targetForm.firstChild);
      } else {
        targetForm.appendChild(container);
      }
    }

    container.innerHTML = '';
    var targetAngle = challengeInfo.target_angle || 135;
    var tolerance = challengeInfo.tolerance || 8;
    var promptText = challengeInfo.prompt || 'Gire el anillo hasta alinear con el objetivo';
    var hintText = challengeInfo.accessible_hint || 'Use las flechas del teclado para girar y Enter para validar';

    var currentAngle = 0;
    var startTime = Date.now();

    // Estilos CSS locales autocontenidos y responsive (cero CDNs)
    var styleId = 'vh-widget-styles';
    if (!document.getElementById(styleId)) {
      var style = document.createElement('style');
      style.id = styleId;
      style.textContent = [
        '#' + this.config.containerId + ' {',
        '  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;',
        '  max-width: 360px; margin: 16px auto; padding: 20px; border-radius: 12px;',
        '  background: #ffffff; border: 1px solid #e2e8f0;',
        '  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); text-align: center; color: #1e293b;',
        '}',
        '.vh-title { font-size: 15px; font-weight: 600; margin-bottom: 8px; color: #0f172a; display: flex; align-items: center; justify-content: center; gap: 8px; }',
        '.vh-subtitle { font-size: 13px; color: #64748b; margin-bottom: 16px; }',
        '.vh-ring-container { position: relative; width: 180px; height: 180px; margin: 0 auto 16px; cursor: pointer; touch-action: none; }',
        '.vh-target-indicator { position: absolute; width: 12px; height: 12px; background: #3b82f6; border-radius: 50%; box-shadow: 0 0 8px #3b82f6; }',
        '.vh-slider-wrapper { margin-bottom: 14px; }',
        '.vh-range-input { width: 100%; height: 6px; border-radius: 3px; background: #e2e8f0; outline: none; cursor: pointer; }',
        '.vh-status { font-size: 12px; font-weight: 500; margin-bottom: 12px; min-height: 18px; }',
        '.vh-status.success { color: #16a34a; }',
        '.vh-status.pending { color: #d97706; }',
        '.vh-btn-confirm { background: #2563eb; color: #ffffff; border: none; padding: 9px 18px; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer; width: 100%; transition: background 0.2s; }',
        '.vh-btn-confirm:hover { background: #1d4ed8; }',
        '.vh-btn-confirm:disabled { background: #94a3b8; cursor: not-allowed; }',
        '.vh-badge { font-size: 11px; color: #94a3b8; margin-top: 10px; display: block; }'
      ].join('\n');
      document.head.appendChild(style);
    }

    var card = document.createElement('div');
    card.setAttribute('role', 'region');
    card.setAttribute('aria-label', 'Desafío de Verificación Humana');

    card.innerHTML = [
      '<div class="vh-title">',
      '  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
      '  <span>Verificación de Seguridad</span>',
      '</div>',
      '<div class="vh-subtitle" id="vh-instruction">' + promptText + '</div>',
      '<div class="vh-ring-container" id="vh-dial" role="slider" tabindex="0"',
      '     aria-label="Selector de alineación angular"',
      '     aria-valuemin="0" aria-valuemax="360" aria-valuenow="0"',
      '     aria-valuetext="0 grados" aria-describedby="vh-instruction">',
      '  <svg width="180" height="180" viewBox="0 0 180 180">',
      '    <circle cx="90" cy="90" r="76" fill="none" stroke="#f1f5f9" stroke-width="12"/>',
      '    <!-- Indicador de objetivo -->',
      '    <circle id="vh-target-dot" cx="90" cy="14" r="8" fill="#3b82f6"/>',
      '    <!-- Indicador móvil rotatorio -->',
      '    <g id="vh-pointer-group" transform="rotate(0 90 90)">',
      '      <line x1="90" y1="90" x2="90" y2="24" stroke="#0f172a" stroke-width="4" stroke-linecap="round"/>',
      '      <circle cx="90" cy="24" r="9" fill="#0f172a"/>',
      '    </g>',
      '  </svg>',
      '</div>',
      '<div class="vh-slider-wrapper">',
      '  <input type="range" class="vh-range-input" id="vh-slider" min="0" max="360" value="0" step="1"',
      '         aria-label="Control deslizante de ángulo de orientación">',
      '</div>',
      '<div class="vh-status pending" id="vh-status-msg">' + hintText + '</div>',
      '<button type="button" class="vh-btn-confirm" id="vh-btn-submit" disabled>Comprobar y Continuar</button>',
      '<span class="vh-badge">Servicio Autónomo Soberano • Venezuela Innova 2026</span>'
    ].join('\n');

    container.appendChild(card);

    // Posicionar el objetivo azul según targetAngle
    var targetRad = (targetAngle - 90) * (Math.PI / 180);
    var targetX = 90 + 76 * Math.cos(targetRad);
    var targetY = 90 + 76 * Math.sin(targetRad);
    var dotEl = document.getElementById('vh-target-dot');
    if (dotEl) {
      dotEl.setAttribute('cx', targetX.toFixed(2));
      dotEl.setAttribute('cy', targetY.toFixed(2));
    }

    var dialEl = document.getElementById('vh-dial');
    var pointerGroup = document.getElementById('vh-pointer-group');
    var sliderEl = document.getElementById('vh-slider');
    var statusMsg = document.getElementById('vh-status-msg');
    var submitBtn = document.getElementById('vh-btn-submit');

    function actualizarAngulo(nuevoAngulo) {
      currentAngle = ((nuevoAngulo % 360) + 360) % 360;
      pointerGroup.setAttribute('transform', 'rotate(' + currentAngle + ' 90 90)');
      dialEl.setAttribute('aria-valuenow', Math.round(currentAngle));
      dialEl.setAttribute('aria-valuetext', Math.round(currentAngle) + ' grados');
      sliderEl.value = Math.round(currentAngle);

      var delta = Math.abs(currentAngle - targetAngle);
      if (delta > 180) delta = 360 - delta;

      if (delta <= tolerance) {
        statusMsg.className = 'vh-status success';
        statusMsg.textContent = '¡Alineación precisa! Presione Enter o el botón para confirmar.';
        submitBtn.disabled = false;
      } else {
        statusMsg.className = 'vh-status pending';
        statusMsg.textContent = 'Diferencia: ' + Math.round(delta) + '°. Continúe ajustando.';
        submitBtn.disabled = true;
      }
    }

    // Navegación por teclado (Flechas Izquierda/Derecha, Arriba/Abajo, Enter)
    dialEl.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight' || e.key === 'ArrowUp') {
        e.preventDefault();
        actualizarAngulo(currentAngle + 15);
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') {
        e.preventDefault();
        actualizarAngulo(currentAngle - 15);
      } else if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        if (!submitBtn.disabled) submitBtn.click();
      }
    });

    sliderEl.addEventListener('input', function (e) {
      actualizarAngulo(parseFloat(e.target.value));
    });

    // Soporte táctil y arrastre sobre el dial
    var isDragging = false;
    function calcularAnguloDesdeEvento(evt) {
      var rect = dialEl.getBoundingClientRect();
      var cx = rect.left + rect.width / 2;
      var cy = rect.top + rect.height / 2;
      var clientX = evt.clientX || (evt.touches && evt.touches[0].clientX) || 0;
      var clientY = evt.clientY || (evt.touches && evt.touches[0].clientY) || 0;
      var rad = Math.atan2(clientY - cy, clientX - cx);
      var deg = rad * (180 / Math.PI) + 90;
      return (deg + 360) % 360;
    }

    dialEl.addEventListener('pointerdown', function (e) {
      isDragging = true;
      actualizarAngulo(calcularAnguloDesdeEvento(e));
    });
    window.addEventListener('pointermove', function (e) {
      if (isDragging) {
        actualizarAngulo(calcularAnguloDesdeEvento(e));
      }
    });
    window.addEventListener('pointerup', function () {
      isDragging = false;
    });

    // Envío del reto resuelto
    submitBtn.addEventListener('click', function () {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Verificando...';

      var duration = Date.now() - startTime;
      var delta = Math.abs(currentAngle - targetAngle);
      if (delta > 180) delta = 360 - delta;
      var precisionDelta = parseFloat((delta / 360).toFixed(4));

      var challengeId = (self.activeChallenge && self.activeChallenge.challenge_id) || self.uuidv4();
      var nonce = (self.activeChallenge && self.activeChallenge.nonce) ? self.activeChallenge.nonce : '8f14e45fceea';
      var diff = (self.activeChallenge && self.activeChallenge.pow_difficulty) ? self.activeChallenge.pow_difficulty : 3;

      solvePoW(nonce, diff).then(function (solution) {
        var verifyUrl = (self.config.apiBase || '') + '/api/v1/challenge/verify';
        var interactivePayload = {
          site_key: self.config.siteKey || 'vh_site_9f8e7d6c5b4a3210',
          challenge_id: challengeId,
          pow_solution: solution,
          telemetry: self.telemetry.computeMetrics(challengeId),
          interactive_response: {
            completed: true,
            interaction_duration_ms: duration,
            precision_delta: precisionDelta
          }
        };

        fetch(verifyUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json; charset=utf-8' },
          body: JSON.stringify(interactivePayload)
        })
          .then(function (res) { return res.json(); })
          .then(function (data) {
            if (data.status === 'verified' && data.jwt_token) {
              self.inyectarToken(data.jwt_token);
              container.innerHTML = [
                '<div style="color: #16a34a; padding: 12px; font-weight: 600;">',
                '  ✓ Verificación humana completada con éxito',
                '</div>'
              ].join('\n');
              setTimeout(function () {
                self.limpiarWidget();
              }, 1200);
              if (typeof self.config.onVerified === 'function') {
                self.config.onVerified(data);
              }
            } else {
              statusMsg.className = 'vh-status pending';
              statusMsg.textContent = 'Intento no válido o precisión insuficiente. Vuelva a intentar.';
              submitBtn.textContent = 'Reintentar';
              submitBtn.disabled = false;
            }
          })
          .catch(function (err) {
            statusMsg.className = 'vh-status error';
            statusMsg.textContent = 'Error al contactar con el backend soberano: ' + (err.message || 'Fallo de red');
            submitBtn.textContent = 'Reintentar';
            submitBtn.disabled = false;
          });
      });
    });
  };

  VerificacionHumanaSDK.prototype.renderizarBloqueo = function (data) {
    this.isBlocked = true;
    this.verifiedToken = null;
    if (typeof document !== 'undefined') {
      document.cookie = 'vh_token=; Max-Age=0; path=/; SameSite=Lax';
    }
    var container = document.getElementById(this.config.containerId);
    if (!container) return;
    container.innerHTML = [
      '<div style="padding: 16px; border: 1px solid #ef4444; background: #fef2f2; border-radius: 8px; color: #991b1b; text-align: center;">',
      '  <strong>Acceso Bloqueado</strong><br>',
      '  <span style="font-size: 13px;">Comportamiento automatizado detectado por la política de seguridad soberana.</span>',
      '</div>'
    ].join('\n');
  };

  VerificacionHumanaSDK.prototype.limpiarWidget = function () {
    var container = document.getElementById(this.config.containerId);
    if (container) {
      container.innerHTML = '';
    }
  };

  VerificacionHumanaSDK.prototype.uuidv4 = function () {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID();
    }
    if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
      var buf = new Uint8Array(16);
      crypto.getRandomValues(buf);
      buf[6] = (buf[6] & 0x0f) | 0x40;
      buf[8] = (buf[8] & 0x3f) | 0x80;
      var hex = Array.from(buf, function (b) { return ('0' + b.toString(16)).slice(-2); }).join('');
      return hex.slice(0, 8) + '-' + hex.slice(8, 12) + '-' + hex.slice(12, 16) + '-' + hex.slice(16, 20) + '-' + hex.slice(20);
    }
    return '10000000-1000-4000-8000-100000000000'.replace(/[018]/g, function (c) {
      return (c ^ (Date.now() & 15) >> (c / 4)).toString(16);
    });
  };

  VerificacionHumanaSDK.prototype.hashSimple = function (str) {
    var hash = 0;
    for (var i = 0; i < str.length; i++) {
      hash = ((hash << 5) - hash) + str.charCodeAt(i);
      hash |= 0;
    }
    return Math.abs(hash).toString(16);
  };

  // Exposición en namespace global y soporte CommonJS / ESM
  var exportTarget = typeof window !== 'undefined' ? window : (typeof global !== 'undefined' ? global : globalThis);
  exportTarget.VerificacionHumana = {
    init: function (config) {
      return new VerificacionHumanaSDK(config);
    },
    TelemetryCollector: TelemetryCollector
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = exportTarget.VerificacionHumana;
  }

  // Autoarranque si hay data-attribute en el script
  if (typeof document !== 'undefined') {
    var currentScript = document.currentScript;
    if (currentScript && currentScript.getAttribute('data-site-key')) {
      var sk = currentScript.getAttribute('data-site-key');
      var base = currentScript.getAttribute('data-api-base') || '';
      exportTarget.VerificacionHumana.instance = new VerificacionHumanaSDK({
        siteKey: sk,
        apiBase: base,
        autoInit: true
      });
    }
  }

})(typeof window !== 'undefined' ? window : (typeof global !== 'undefined' ? global : this));
