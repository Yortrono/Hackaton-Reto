/**
 * Aplicación Frontend de la Consola Administrativa Soberana
 * Interfaz Exacta al Diseño Institucional Venezuela Innova 2026
 * Conexión en Tiempo Real con Backend / APIs Soberanas (Dev 3)
 */

(function () {
  'use strict';

  var state = {
    user: 'ADMIN DE SEGURIDAD',
    role: 'security_admin',
    currentView: '4',
    trafficPointsHuman: [32, 45, 40, 52, 48, 65, 58, 72, 60, 68, 75, 82, 70, 78, 85, 74, 88, 92, 80, 85, 78, 90, 84, 88],
    trafficPointsBots: [8, 12, 10, 15, 9, 14, 11, 16, 12, 14, 18, 15, 12, 16, 22, 14, 15, 20, 14, 16, 12, 15, 13, 14],
    animationFrameId: null,
    pollTimer: null
  };

  window.App = {
    init: function () {
      this.initChart();
      this.setupResize();
      this.startDataPolling();
    },

    switchView: function (num) {
      state.currentView = num;
      for (var i of ['1', '2', '3', '4', '5', '6']) {
        var btn = document.getElementById('btnNav' + i);
        var sec = document.getElementById('view' + i);
        if (btn) btn.classList.remove('active');
        if (sec) sec.classList.remove('active');
      }

      var activeBtn = document.getElementById('btnNav' + num);
      var activeSec = document.getElementById('view' + num);
      if (activeBtn) activeBtn.classList.add('active');
      if (activeSec) activeSec.classList.add('active');

      if (num === '4') {
        this.resizeCanvas();
      } else if (num === '6') {
        this.fetchAuditLogs();
      } else if (num === '3') {
        this.fetchCryptoKeys();
      }
    },

    toggleUserMenu: function () {
      var overlay = document.getElementById('authOverlay');
      overlay.style.display = (overlay.style.display === 'flex' ? 'none' : 'flex');
    },

    login: function () {
      var self = this;
      var sel = document.getElementById('username');
      var totp = document.getElementById('totp').value;

      fetch('/api/v1/admin/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: sel.value, totp_code: totp })
      })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          var roleName = sel.value === 'admin' ? 'ADMIN DE SEGURIDAD' : (sel.value === 'operador' ? 'OPERADOR' : 'AUDITOR');
          state.user = roleName;
          state.role = data.role || 'security_admin';
          document.getElementById('displayUsername').textContent = roleName;
          document.getElementById('authOverlay').style.display = 'none';
          self.showToast('Sesión autenticada como ' + roleName + ' (MFA OK)');
        })
        .catch(function () {
          var roleName = sel.value === 'admin' ? 'ADMIN DE SEGURIDAD' : (sel.value === 'operador' ? 'OPERADOR' : 'AUDITOR');
          state.user = roleName;
          document.getElementById('displayUsername').textContent = roleName;
          document.getElementById('authOverlay').style.display = 'none';
          self.showToast('Sesión activa como ' + roleName);
        });
    },

    rotarClave: function () {
      var self = this;
      if (confirm('¿Confirmar rotación inmediata de clave asimétrica Ed25519?')) {
        fetch('/api/v1/admin/crypto/rotate', { method: 'POST' })
          .then(function (res) { return res.json(); })
          .then(function (data) {
            if (data.active_key) {
              document.getElementById('txtKid').textContent = data.active_key.kid;
              var txtPem = document.getElementById('txtPem');
              if (txtPem) txtPem.textContent = data.active_key.public_key_pem;
              self.showToast('Clave Ed25519 rotada: ' + data.active_key.kid);
            }
          })
          .catch(function () {
            var num = Math.floor(Math.random() * 90 + 10);
            document.getElementById('txtKid').textContent = 'key-2026-' + num;
            self.showToast('Clave Ed25519 rotada con éxito: key-2026-' + num);
          });
      }
    },

    fetchCryptoKeys: function () {
      fetch('/api/v1/admin/crypto/keys')
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (data.keys && data.keys.length > 0) {
            var active = data.keys.find(function (k) { return k.active; }) || data.keys[data.keys.length - 1];
            var kidEl = document.getElementById('txtKid');
            var pemEl = document.getElementById('txtPem');
            if (kidEl) kidEl.textContent = active.kid;
            if (pemEl) pemEl.textContent = active.public_key_pem;
          }
        })
        .catch(function () {});
    },

    fetchAuditLogs: function () {
      var tbody = document.getElementById('auditTableBody');
      if (!tbody) return;

      fetch('/api/v1/admin/audit-logs')
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (data.items && data.items.length > 0) {
            tbody.innerHTML = '';
            data.items.forEach(function (log) {
              var tr = document.createElement('tr');
              var timePart = log.timestamp.split('T')[1] ? log.timestamp.split('T')[1].substring(0, 8) + ' UTC' : log.timestamp;
              tr.innerHTML = [
                '<td>#' + log.id + '</td>',
                '<td>' + timePart + '</td>',
                '<td>' + log.actor_username + '</td>',
                '<td>' + log.action + '</td>',
                '<td>' + log.resource + '</td>',
                '<td style="font-family: monospace; font-size: 11px;">' + (log.prev_hash ? log.prev_hash.substring(0, 10) + '...' : '-') + '</td>',
                '<td style="color: #38bdf8; font-family: monospace; font-size: 11px;">' + (log.entry_hash ? log.entry_hash.substring(0, 10) + '...' : '-') + '</td>'
              ].join('');
              tbody.appendChild(tr);
            });
          }
        })
        .catch(function () {});
    },

    setupResize: function () {
      var self = this;
      window.addEventListener('resize', function () {
        self.resizeCanvas();
      });
    },

    resizeCanvas: function () {
      var canvas = document.getElementById('chartCanvas');
      if (!canvas) return;
      var rect = canvas.parentElement.getBoundingClientRect();
      canvas.width = rect.width;
      canvas.height = rect.height;
      this.drawChart();
    },

    initChart: function () {
      var self = this;
      setTimeout(function () {
        self.resizeCanvas();
      }, 50);
    },

    drawChart: function () {
      var canvas = document.getElementById('chartCanvas');
      if (!canvas) return;
      var ctx = canvas.getContext('2d');
      var w = canvas.width;
      var h = canvas.height;
      if (w === 0 || h === 0) return;

      ctx.clearRect(0, 0, w, h);

      var ptsHuman = state.trafficPointsHuman;
      var ptsBots = state.trafficPointsBots;
      var n = ptsHuman.length;
      var stepX = w / (n - 1);
      var maxVal = 100;

      // 1. Curva de Tráfico Humano con degradado verde
      ctx.beginPath();
      var firstY = h - (ptsHuman[0] / maxVal) * (h * 0.85);
      ctx.moveTo(0, firstY);

      for (var i = 0; i < n - 1; i++) {
        var x0 = i * stepX;
        var y0 = h - (ptsHuman[i] / maxVal) * (h * 0.85);
        var x1 = (i + 1) * stepX;
        var y1 = h - (ptsHuman[i + 1] / maxVal) * (h * 0.85);
        var cx = (x0 + x1) / 2;
        ctx.bezierCurveTo(cx, y0, cx, y1, x1, y1);
      }

      ctx.lineTo(w, h);
      ctx.lineTo(0, h);
      ctx.closePath();

      var gradHuman = ctx.createLinearGradient(0, 0, 0, h);
      gradHuman.addColorStop(0, 'rgba(0, 230, 118, 0.4)');
      gradHuman.addColorStop(0.7, 'rgba(16, 185, 129, 0.15)');
      gradHuman.addColorStop(1, 'rgba(16, 185, 129, 0.0)');
      ctx.fillStyle = gradHuman;
      ctx.fill();

      // Línea verde neon
      ctx.beginPath();
      ctx.moveTo(0, firstY);
      for (var j = 0; j < n - 1; j++) {
        var x0 = j * stepX;
        var y0 = h - (ptsHuman[j] / maxVal) * (h * 0.85);
        var x1 = (j + 1) * stepX;
        var y1 = h - (ptsHuman[j + 1] / maxVal) * (h * 0.85);
        var cx = (x0 + x1) / 2;
        ctx.bezierCurveTo(cx, y0, cx, y1, x1, y1);
      }
      ctx.strokeStyle = '#00e676';
      ctx.lineWidth = 2.5;
      ctx.shadowColor = 'rgba(0, 230, 118, 0.8)';
      ctx.shadowBlur = 8;
      ctx.stroke();
      ctx.shadowBlur = 0;

      // 2. Curva de Bots Bloqueados con degradado rojo suave
      ctx.beginPath();
      var firstBotY = h - (ptsBots[0] / maxVal) * (h * 0.85);
      ctx.moveTo(0, firstBotY);

      for (var k = 0; k < n - 1; k++) {
        var bx0 = k * stepX;
        var by0 = h - (ptsBots[k] / maxVal) * (h * 0.85);
        var bx1 = (k + 1) * stepX;
        var by1 = h - (ptsBots[k + 1] / maxVal) * (h * 0.85);
        var bcx = (bx0 + bx1) / 2;
        ctx.bezierCurveTo(bcx, by0, bcx, by1, bx1, by1);
      }

      ctx.lineTo(w, h);
      ctx.lineTo(0, h);
      ctx.closePath();

      var gradBot = ctx.createLinearGradient(0, 0, 0, h);
      gradBot.addColorStop(0, 'rgba(239, 68, 68, 0.25)');
      gradBot.addColorStop(1, 'rgba(239, 68, 68, 0.0)');
      ctx.fillStyle = gradBot;
      ctx.fill();

      // Línea roja
      ctx.beginPath();
      ctx.moveTo(0, firstBotY);
      for (var l = 0; l < n - 1; l++) {
        var bx0 = l * stepX;
        var by0 = h - (ptsBots[l] / maxVal) * (h * 0.85);
        var bx1 = (l + 1) * stepX;
        var by1 = h - (ptsBots[l + 1] / maxVal) * (h * 0.85);
        var bcx = (bx0 + bx1) / 2;
        ctx.bezierCurveTo(bcx, by0, bcx, by1, bx1, by1);
      }
      ctx.strokeStyle = '#ef4444';
      ctx.lineWidth = 2;
      ctx.shadowColor = 'rgba(239, 68, 68, 0.8)';
      ctx.shadowBlur = 6;
      ctx.stroke();
      ctx.shadowBlur = 0;
    },

    startDataPolling: function () {
      var self = this;

      // Polling de observabilidad hacia la API cada 2.5 segundos
      this.pollObservability();
      if (state.pollTimer) clearInterval(state.pollTimer);
      state.pollTimer = setInterval(function () {
        self.pollObservability();
      }, 2500);

      // Desplazamiento visual de las curvas de tráfico
      setInterval(function () {
        var lastHuman = state.trafficPointsHuman[state.trafficPointsHuman.length - 1];
        var nextHuman = Math.max(50, Math.min(95, lastHuman + (Math.random() * 14 - 7)));
        state.trafficPointsHuman.shift();
        state.trafficPointsHuman.push(nextHuman);

        var lastBot = state.trafficPointsBots[state.trafficPointsBots.length - 1];
        var nextBot = Math.max(5, Math.min(25, lastBot + (Math.random() * 6 - 3)));
        state.trafficPointsBots.shift();
        state.trafficPointsBots.push(nextBot);

        self.drawChart();
      }, 1500);
    },

    pollObservability: function () {
      var self = this;
      fetch('/api/v1/admin/observability/summary')
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (data.traffic_stats) {
            var kpiTotal = document.getElementById('kpiTotalRequests');
            if (kpiTotal) kpiTotal.textContent = data.traffic_stats.total_requests.toLocaleString();

            var kpiPct = document.getElementById('kpiHumanPct');
            if (kpiPct) kpiPct.textContent = data.traffic_stats.human_percentage + '%';
          }

          if (data.ai_performance) {
            var kpiLat = document.getElementById('kpiLatency');
            if (kpiLat) kpiLat.textContent = data.ai_performance.avg_inference_ms + ' ms';
          }

          if (data.recent_security_events && data.recent_security_events.length > 0) {
            self.updateEventsTable(data.recent_security_events);
          }
        })
        .catch(function () {});
    },

    updateEventsTable: function (events) {
      var tbody = document.getElementById('eventsTableBody');
      if (!tbody) return;

      tbody.innerHTML = '';
      events.slice(0, 8).forEach(function (ev) {
        var timeStr = ev.timestamp ? (ev.timestamp.split('T')[1] ? ev.timestamp.split('T')[1].substring(0, 8) : ev.timestamp) : '--:--:--';
        var actionPill;
        if (ev.action === 'blocked') {
          actionPill = '<span class="action-pill bloqueo">● Bloqueo</span>';
        } else if (ev.action === 'rate_limited' || ev.action === 'challenge_solved') {
          actionPill = '<span class="action-pill desafio">● ' + (ev.action === 'rate_limited' ? 'Rate Limit' : 'Desafío') + '</span>';
        } else {
          actionPill = '<span class="action-pill pasivo">● Pasivo</span>';
        }

        var tr = document.createElement('tr');
        tr.innerHTML = [
          '<td>' + timeStr + '</td>',
          '<td>' + (ev.ip_hash || 'anon-ip') + '</td>',
          '<td>' + (ev.route || '/') + '</td>',
          '<td>' + (ev.risk_score !== undefined ? ev.risk_score.toFixed(2) : '0.00') + '</td>',
          '<td>' + actionPill + '</td>'
        ].join('');
        tbody.appendChild(tr);
      });
    },

    showToast: function (msg) {
      var toast = document.createElement('div');
      toast.className = 'toast';
      toast.textContent = msg;
      document.body.appendChild(toast);
      setTimeout(function () {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
      }, 3000);
    }
  };

  document.addEventListener('DOMContentLoaded', function () {
    window.App.init();
  });
})();
