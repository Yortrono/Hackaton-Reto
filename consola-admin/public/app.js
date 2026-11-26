/**
 * Aplicación Frontend de la Consola Administrativa Soberana
 * Interfaz Exacta al Diseño Institucional Venezuela Innova 2026
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
      this.setupResize();
      var isAuth = sessionStorage.getItem('vh_authenticated') === 'true';
      var overlay = document.getElementById('authOverlay');

      if (isAuth) {
        if (overlay) overlay.style.display = 'none';
        var savedUser = sessionStorage.getItem('vh_display_user') || 'ADMIN DE SEGURIDAD';
        var savedRole = sessionStorage.getItem('vh_role') || 'security_admin';
        state.user = savedUser;
        state.role = savedRole;
        this.updateUserDisplay();
        this.initChart();
        this.startDataSimulation();
      } else {
        if (overlay) overlay.style.display = 'flex';
      }
    },

    updateUserDisplay: function () {
      var dUser = document.getElementById('displayUsername');
      var dropName = document.getElementById('dropUserName');
      var dropRole = document.getElementById('dropRoleTag');
      if (dUser) dUser.textContent = state.user;
      if (dropName) dropName.textContent = state.user;
      if (dropRole) dropRole.textContent = 'Rol: ' + state.role;
    },

    toggleUserMenu: function () {
      var dropdown = document.getElementById('userDropdown');
      if (dropdown) {
        dropdown.classList.toggle('open');
      }
    },

    logout: function () {
      sessionStorage.removeItem('vh_authenticated');
      sessionStorage.removeItem('vh_display_user');
      sessionStorage.removeItem('vh_role');
      var dropdown = document.getElementById('userDropdown');
      if (dropdown) dropdown.classList.remove('open');
      var overlay = document.getElementById('authOverlay');
      if (overlay) overlay.style.display = 'flex';
      this.showToast('Sesión cerrada correctamente');
    },

    login: function () {
      var self = this;
      var sel = document.getElementById('username');
      var username = sel ? sel.value : 'admin';
      var totp = document.getElementById('totp') ? document.getElementById('totp').value.trim() : '';

      if (totp !== '123456') {
        self.showToast('Código MFA inválido. Ingrese 123456');
        return;
      }

      var roleMap = {
        admin: { title: 'ADMIN DE SEGURIDAD', role: 'security_admin' },
        operador: { title: 'OPERADOR DE MITIGACIÓN', role: 'operator' },
        auditor: { title: 'AUDITOR DE CUMPLIMIENTO', role: 'auditor' }
      };

      var roleData = roleMap[username] || roleMap.admin;
      state.user = roleData.title;
      state.role = roleData.role;

      sessionStorage.setItem('vh_authenticated', 'true');
      sessionStorage.setItem('vh_display_user', state.user);
      sessionStorage.setItem('vh_role', state.role);

      self.updateUserDisplay();

      var overlay = document.getElementById('authOverlay');
      if (overlay) overlay.style.display = 'none';

      self.showToast('Autenticación MFA exitosa. Bienvenido');
      self.initChart();
      self.startDataSimulation();
    },

    onRoleChange: function (val) {
      // Cambio opcional
    },

    rotarClave: function () {
      if (confirm('¿Confirmar rotación inmediata de clave asimétrica Ed25519?')) {
        var num = Math.floor(Math.random() * 90 + 10);
        document.getElementById('txtKid').textContent = 'key-2026-' + num;
        this.showToast('Clave Ed25519 rotada con éxito: key-2026-' + num);
      }
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

      // 1. Dibujar curva suave de Tráfico Humano con degradado verde
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

      // Cerrar área para el degradado verde
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

      // 2. Dibujar curva de Bots Bloqueados con degradado rojo suave
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

    startDataSimulation: function () {
      var self = this;
      setInterval(function () {
        // Desplazar puntos de la gráfica simulando flujo en tiempo real
        var lastHuman = state.trafficPointsHuman[state.trafficPointsHuman.length - 1];
        var nextHuman = Math.max(50, Math.min(95, lastHuman + (Math.random() * 16 - 8)));
        state.trafficPointsHuman.shift();
        state.trafficPointsHuman.push(nextHuman);

        var lastBot = state.trafficPointsBots[state.trafficPointsBots.length - 1];
        var nextBot = Math.max(5, Math.min(25, lastBot + (Math.random() * 6 - 3)));
        state.trafficPointsBots.shift();
        state.trafficPointsBots.push(nextBot);

        // Actualizar KPIs sutilmente
        var totalReq = 14820 + Math.floor(Math.random() * 20 - 10);
        document.getElementById('kpiTotalRequests').textContent = totalReq.toLocaleString();

        var latency = (18.2 + Math.random() * 0.6).toFixed(1);
        document.getElementById('kpiLatency').textContent = latency + ' ms';

        self.drawChart();
      }, 1500);

      // Agregar eventos nuevos periódicos a la tabla
      setInterval(function () {
        self.addNewEvent();
      }, 4000);
    },

    addNewEvent: function () {
      var tbody = document.getElementById('eventsTableBody');
      if (!tbody) return;

      var now = new Date();
      var timeStr = now.toTimeString().split(' ')[0];
      var rand = Math.random();
      var hash = Math.random().toString(16).substring(2, 6) + '...' + Math.random().toString(16).substring(2, 6);

      var route, score, actionPill;
      if (rand > 0.4) {
        route = '/login';
        score = (0.05 + Math.random() * 0.15).toFixed(2);
        actionPill = '<span class="action-pill pasivo">● Pasivo</span>';
      } else if (rand > 0.15) {
        route = '/registro';
        score = (0.55 + Math.random() * 0.15).toFixed(2);
        actionPill = '<span class="action-pill desafio">● Desafío</span>';
      } else {
        route = '/api/auth';
        score = (0.88 + Math.random() * 0.11).toFixed(2);
        actionPill = '<span class="action-pill bloqueo">● Bloqueo</span>';
      }

      var tr = document.createElement('tr');
      tr.innerHTML = [
        '<td>' + timeStr + '</td>',
        '<td>' + hash + '</td>',
        '<td>' + route + '</td>',
        '<td>' + score + '</td>',
        '<td>' + actionPill + '</td>'
      ].join('');

      tbody.insertBefore(tr, tbody.firstChild);
      if (tbody.children.length > 7) {
        tbody.removeChild(tbody.lastChild);
      }
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
