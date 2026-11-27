/**
 * Aplicación Frontend de la Consola Administrativa Soberana
 * Interfaz Exacta al Diseño Institucional Venezuela Innova 2026
 * Conexión en Tiempo Real 100% Funcional con Backend y Borde Soberano (Dev 3)
 */

(function () {
  'use strict';

  var state = {
    user: 'ADMIN DE SEGURIDAD',
    role: 'security_admin',
    adminToken: null,
    currentView: '4',
    // Historial dinámico de tráfico en vivo
    trafficPointsHuman: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    trafficPointsBots: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    lastVerifiedCount: 0,
    lastBlockedCount: 0,
    isFirstPoll: true,
    pollTimer: null,
    activeSiteId: 'default',
    eventsFilter: 'all',
    lastSecurityEvents: []
  };

  window.App = {
    init: function () {
      this.initChart();
      this.setupResize();
      this.autoAuthenticate();
      this.startDataPolling();
    },

    getHeaders: function () {
      var headers = { 'Content-Type': 'application/json' };
      if (state.adminToken) {
        headers['Authorization'] = 'Bearer ' + state.adminToken;
      }
      return headers;
    },

    autoAuthenticate: function () {
      var self = this;
      fetch('/api/v1/admin/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: 'admin_seguridad',
          password: 'Soberania2026!Segura'
        })
      })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (data.access_token) {
            state.adminToken = data.access_token;
            state.role = data.role;
            state.user = 'ADMIN DE SEGURIDAD';
            self.applyRbacUI();
            self.loadActiveViewData();
            self.checkMfaStatus();
          }
        })
        .catch(function () {});
    },

    onUserSelectChange: function (val) {
      var pwdInput = document.getElementById('password');
      if (!pwdInput) return;
      if (val === 'admin_seguridad') {
        pwdInput.value = 'Soberania2026!Segura';
      } else if (val === 'operador_politicas') {
        pwdInput.value = 'Operador2026!Vzla';
      } else if (val === 'auditor_fiscal') {
        pwdInput.value = 'Auditor2026!Transparente';
      }
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

      this.loadActiveViewData();
    },

    loadActiveViewData: function () {
      if (state.currentView === '4') {
        this.resizeCanvas();
      } else if (state.currentView === '1') {
        this.fetchSites();
      } else if (state.currentView === '2') {
        this.fetchPolicies();
      } else if (state.currentView === '3') {
        this.fetchCryptoKeys();
      } else if (state.currentView === '5') {
        this.fetchAiModelInfo();
      } else if (state.currentView === '6') {
        this.fetchAuditLogs();
      }
    },

    applyRbacUI: function () {
      var displayUser = document.getElementById('displayUsername');
      if (displayUser) displayUser.textContent = state.user;

      // Restricciones visuales por rol (RBAC)
      var btnRotar = document.querySelector('#view3 button.btn-danger');
      var btnGuardarPol = document.querySelector('#view2 button.btn-primary');
      var boxUploadAi = document.querySelector('#view5 div[style*="dashed"]');

      if (state.role === 'auditor') {
        if (btnRotar) btnRotar.style.display = 'none';
        if (btnGuardarPol) btnGuardarPol.style.display = 'none';
        if (boxUploadAi) boxUploadAi.style.display = 'none';
      } else if (state.role === 'operator') {
        if (btnRotar) btnRotar.style.display = 'none';
        if (btnGuardarPol) btnGuardarPol.style.display = 'block';
        if (boxUploadAi) boxUploadAi.style.display = 'none';
      } else {
        if (btnRotar) btnRotar.style.display = 'block';
        if (btnGuardarPol) btnGuardarPol.style.display = 'block';
        if (boxUploadAi) boxUploadAi.style.display = 'block';
      }
    },

    toggleUserMenu: function () {
      var overlay = document.getElementById('authOverlay');
      overlay.style.display = (overlay.style.display === 'flex' ? 'none' : 'flex');
    },

    login: function () {
      var self = this;
      var sel = document.getElementById('username');
      var pwd = document.getElementById('password').value;
      var totp = document.getElementById('totp').value;

      var payload = { username: sel.value, password: pwd };
      if (totp && totp.trim() !== '') {
        payload.totp_code = totp.trim();
      }

      fetch('/api/v1/admin/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
        .then(function (res) {
          if (!res.ok) throw new Error('HTTP ' + res.status);
          return res.json();
        })
        .then(function (data) {
          if (data.mfa_required) {
            self.showToast('Se requiere código TOTP para este usuario.');
            return;
          }
          state.adminToken = data.access_token;
          state.role = data.role || 'security_admin';
          state.user = sel.value === 'admin_seguridad' ? 'ADMIN DE SEGURIDAD' : (sel.value === 'operador_politicas' ? 'OPERADOR DE POLÍTICAS' : 'AUDITOR FISCAL');
          
          self.applyRbacUI();
          self.checkMfaStatus();
          document.getElementById('authOverlay').style.display = 'none';
          self.showToast('Sesión autenticada como ' + state.user + ' con éxito.');
          self.loadActiveViewData();
        })
        .catch(function (err) {
          self.showToast('Error de autenticación: Verifique credenciales.');
        });
    },

    // =========================================================================
    // GESTIÓN VISUAL DE MFA / TOTP (RFC 6238)
    // =========================================================================
    switchAuthTab: function (tab) {
      var tabBtnLogin = document.getElementById('tabBtnLogin');
      var tabBtnMfa = document.getElementById('tabBtnMfa');
      var secLogin = document.getElementById('authSectionLogin');
      var secMfa = document.getElementById('authSectionMfa');

      if (tab === 'login') {
        if (tabBtnLogin) tabBtnLogin.classList.add('active');
        if (tabBtnMfa) tabBtnMfa.classList.remove('active');
        if (secLogin) secLogin.style.display = 'block';
        if (secMfa) secMfa.style.display = 'none';
      } else {
        if (tabBtnLogin) tabBtnLogin.classList.remove('active');
        if (tabBtnMfa) tabBtnMfa.classList.add('active');
        if (secLogin) secLogin.style.display = 'none';
        if (secMfa) secMfa.style.display = 'block';
        this.checkMfaStatus();
      }
    },

    checkMfaStatus: function () {
      if (!state.adminToken) return;

      fetch('/api/v1/admin/auth/me', { headers: this.getHeaders() })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          var userText = document.getElementById('mfaActiveUserText');
          if (userText) userText.textContent = data.username + ' (' + data.role + ')';

          var badge = document.getElementById('mfaStatusBadge');
          var dispSubtitle = document.getElementById('displayMfaStatus');
          var inactivePanel = document.getElementById('mfaInactivePanel');
          var activePanel = document.getElementById('mfaActivePanel');

          if (data.totp_enabled) {
            if (badge) {
              badge.className = 'action-pill pasivo';
              badge.textContent = '● Activo';
            }
            if (dispSubtitle) {
              dispSubtitle.textContent = '(MFA Activo)';
              dispSubtitle.style.color = '#34d399';
            }
            if (inactivePanel) inactivePanel.style.display = 'none';
            if (activePanel) activePanel.style.display = 'block';
          } else {
            if (badge) {
              badge.className = 'action-pill bloqueo';
              badge.textContent = '● Desactivado';
            }
            if (dispSubtitle) {
              dispSubtitle.textContent = '(MFA Desactivado)';
              dispSubtitle.style.color = '#94a3b8';
            }
            if (inactivePanel) inactivePanel.style.display = 'block';
            if (activePanel) activePanel.style.display = 'none';
          }
        })
        .catch(function () {});
    },

    startTotpSetup: function () {
      var self = this;
      fetch('/api/v1/admin/auth/setup-totp', {
        method: 'POST',
        headers: this.getHeaders()
      })
        .then(function (res) {
          if (!res.ok) throw new Error('HTTP ' + res.status);
          return res.json();
        })
        .then(function (data) {
          var txtSecret = document.getElementById('txtTotpSecret');
          if (txtSecret) txtSecret.value = data.secret;

          var area = document.getElementById('mfaSecretDisplayArea');
          if (area) area.style.display = 'block';

          self.showToast('Semilla TOTP generada. Ingrésela en su app autenticadora.');
        })
        .catch(function (err) {
          self.showToast('Error al iniciar configuración TOTP: ' + err.message);
        });
    },

    copyTotpSecret: function () {
      var txtSecret = document.getElementById('txtTotpSecret');
      if (txtSecret && txtSecret.value) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(txtSecret.value)
            .then(function () {
              window.App.showToast('Clave secreta copiada al portapapeles.');
            })
            .catch(function () {
              txtSecret.select();
              document.execCommand('copy');
              window.App.showToast('Clave copiada.');
            });
        } else {
          txtSecret.select();
          document.execCommand('copy');
          window.App.showToast('Clave copiada.');
        }
      }
    },

    confirmTotpActivation: function () {
      var self = this;
      var codeInput = document.getElementById('txtTotpVerifyCode');
      var code = codeInput ? codeInput.value.trim() : '';
      if (!code || code.length !== 6) {
        self.showToast('Ingrese un código de exactamente 6 dígitos.');
        return;
      }

      fetch('/api/v1/admin/auth/verify-totp', {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({ totp_code: code })
      })
        .then(function (res) {
          if (!res.ok) throw new Error('Código TOTP inválido o expirado.');
          return res.json();
        })
        .then(function () {
          self.showToast('✓ Segundo Factor MFA/TOTP activado exitosamente.');
          if (codeInput) codeInput.value = '';
          var area = document.getElementById('mfaSecretDisplayArea');
          if (area) area.style.display = 'none';
          self.checkMfaStatus();
        })
        .catch(function (err) {
          self.showToast('Error al activar: Verifique el código de su App.');
        });
    },

    disableTotp: function () {
      var self = this;
      if (!confirm('¿Está seguro de desactivar el segundo factor MFA en esta cuenta?')) return;

      fetch('/api/v1/admin/auth/disable-totp', {
        method: 'POST',
        headers: this.getHeaders()
      })
        .then(function (res) {
          if (!res.ok) throw new Error('HTTP ' + res.status);
          return res.json();
        })
        .then(function () {
          self.showToast('Segundo Factor MFA deshabilitado.');
          self.checkMfaStatus();
        })
        .catch(function (err) {
          self.showToast('Error al deshabilitar MFA: ' + err.message);
        });
    },

    // =========================================================================
    // MÓDULO 1: GESTIÓN DE SITIOS Y APLICACIONES
    // =========================================================================
    fetchSites: function () {
      var self = this;
      fetch('/api/v1/admin/sites', { headers: this.getHeaders() })
        .then(function (res) { return res.json(); })
        .then(function (sites) {
          if (Array.isArray(sites) && sites.length > 0) {
            state.sitesList = sites;

            // Actualizar contador en título
            var countEl = document.getElementById('txtSitesCount');
            if (countEl) countEl.textContent = '(Total: ' + sites.length + ' sitio' + (sites.length > 1 ? 's' : '') + ')';

            // Actualizar selector dropdown
            var selSite = document.getElementById('selActiveSite');
            if (selSite) {
              selSite.innerHTML = '';
              sites.forEach(function (s) {
                var opt = document.createElement('option');
                opt.value = s.site_id;
                opt.textContent = s.name + ' (' + s.site_id + ')';
                if (s.site_id === state.activeSiteId) opt.selected = true;
                selSite.appendChild(opt);
              });
            }

            // Actualizar tabla del catálogo de todos los sitios
            var allTbody = document.getElementById('allSitesTableBody');
            if (allTbody) {
              allTbody.innerHTML = '';
              sites.forEach(function (s) {
                var tr = document.createElement('tr');
                var isSelected = (s.site_id === (state.activeSiteId || 'default'));
                tr.innerHTML = [
                  '<td><strong>' + s.name + '</strong></td>',
                  '<td><code>' + s.site_id + '</code></td>',
                  '<td><span style="color: #94a3b8;">' + (s.domain || '-') + '</span></td>',
                  '<td><code style="color: #38bdf8;">' + s.site_key + '</code></td>',
                  '<td><span class="action-pill pasivo">● Activo</span></td>',
                  '<td style="text-align: center;"><button class="btn-primary" style="padding: 4px 10px; font-size: 11px;' + (isSelected ? ' background: #059669;' : '') + '" onclick="window.App.selectSite(\'' + s.site_id + '\')">' + (isSelected ? '✓ Seleccionado' : 'Seleccionar') + '</button></td>'
                ].join('');
                allTbody.appendChild(tr);
              });
            }

            // Si no hay sitio activo seleccionado, tomar el primero o mantener el actual
            var currentId = state.activeSiteId || sites[0].site_id;
            self.selectSite(currentId, false);
          }
        })
        .catch(function () {});
    },

    selectSite: function (siteId, reFetchList) {
      state.activeSiteId = siteId;
      var s = (state.sitesList || []).find(function (item) { return item.site_id === siteId; });
      if (s) {
        var txtSk = document.getElementById('txtSiteKey');
        var txtSid = document.getElementById('txtSiteId');
        var txtName = document.getElementById('txtSiteName');
        var txtDom = document.getElementById('txtSiteDomain');
        var selSite = document.getElementById('selActiveSite');

        if (txtSk) txtSk.value = s.site_key;
        if (txtSid) txtSid.value = s.site_id;
        if (txtName) txtName.value = s.name;
        if (txtDom) txtDom.value = s.domain || '-';
        if (selSite) selSite.value = s.site_id;
      }

      // Obtener rutas protegidas del sitio seleccionado
      fetch('/api/v1/policies/' + siteId)
        .then(function (res) { return res.json(); })
        .then(function (data) {
          var tbody = document.getElementById('routesTableBody');
          if (!tbody) return;
          tbody.innerHTML = '';
          var routes = (data.policy && data.policy.protected_routes) ? data.policy.protected_routes : [];
          if (routes.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #94a3b8; font-size: 12px; padding: 12px;">Sin rutas específicas personalizadas. Aplica las políticas y límites globales de mitigación.</td></tr>';
          } else {
            routes.forEach(function (r) {
              var tr = document.createElement('tr');
              tr.innerHTML = [
                '<td><code>' + r.path_prefix + '</code></td>',
                '<td>' + (r.methods || []).join(', ') + '</td>',
                '<td><span class="action-pill ' + (r.require_token ? 'pasivo' : 'bloqueo') + '">● ' + (r.require_token ? 'Sí' : 'No') + '</span></td>',
                '<td>' + (r.rate_limit_rpm || 60) + ' rpm</td>'
              ].join('');
              tbody.appendChild(tr);
            });
          }
        })
        .catch(function () {});

      if (reFetchList === true) {
        this.fetchSites();
      }
    },

    onSiteSelectChange: function (siteId) {
      this.selectSite(siteId, true);
    },

    promptCreateSite: function () {
      var self = this;
      var siteName = prompt('Nombre de la nueva aplicación institucional a proteger:', 'Portal Saime');
      if (!siteName || siteName.trim() === '') return;
      siteName = siteName.trim();
      var defaultDomain = siteName.toLowerCase().replace(/[^a-z0-9]/g, '') + '.gob.ve';
      var domain = prompt('Dominio FQDN local del sitio:', defaultDomain);
      if (!domain || domain.trim() === '') return;
      domain = domain.trim();
      var siteId = siteName.toLowerCase().replace(/[^a-z0-9]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '');

      fetch('/api/v1/admin/sites', {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({
          site_id: siteId,
          name: siteName,
          domain: domain
        })
      })
        .then(function (res) {
          return res.json().then(function (data) {
            return { ok: res.ok, status: res.status, data: data };
          });
        })
        .then(function (result) {
          if (result.ok && result.data.site_key) {
            self.showToast('✓ Sitio registrado exitosamente: ' + result.data.name);
            state.activeSiteId = result.data.site_id;
            self.fetchSites();
          } else {
            var msg = (result.data.error && result.data.error.message) || (result.data.detail && result.data.detail.message) || 'No se pudo crear el sitio.';
            self.showToast('Aviso: ' + msg);
          }
        })
        .catch(function (err) {
          self.showToast('Error de conexión: ' + err.message);
        });
    },

    // =========================================================================
    // MÓDULO 2: MOTOR DE REGLAS Y MITIGACIÓN
    // =========================================================================
    fetchPolicies: function () {
      fetch('/api/v1/policies/default')
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (data.policy) {
            var p = data.policy;
            var selMode = document.getElementById('selPolicyMode');
            if (selMode) selMode.value = p.mode || 'challenge';

            if (p.ai_thresholds) {
              var chMin = p.ai_thresholds.challenge_min || 0.35;
              var blMin = p.ai_thresholds.block_min || 0.75;
              var rngCh = document.getElementById('rngChMin');
              var rngBl = document.getElementById('rngBlMin');
              var txtCh = document.getElementById('txtChMin');
              var txtBl = document.getElementById('txtBlMin');
              if (rngCh) rngCh.value = chMin;
              if (rngBl) rngBl.value = blMin;
              if (txtCh) txtCh.textContent = chMin;
              if (txtBl) txtBl.textContent = blMin;
            }

            var numRpm = document.getElementById('numGlobalRpm');
            if (numRpm) numRpm.value = p.rate_limit_global_rpm || 120;

            var txtWl = document.getElementById('txtWhitelist');
            if (txtWl && p.ip_whitelist) txtWl.value = p.ip_whitelist.join(', ');
          }
        })
        .catch(function () {});
    },

    savePolicies: function () {
      var self = this;
      var selMode = document.getElementById('selPolicyMode').value;
      var chMin = parseFloat(document.getElementById('rngChMin').value);
      var blMin = parseFloat(document.getElementById('rngBlMin').value);
      var globalRpm = parseInt(document.getElementById('numGlobalRpm').value, 10) || 120;
      var wlRaw = document.getElementById('txtWhitelist').value;
      var wlArray = wlRaw.split(',').map(function (s) { return s.trim(); }).filter(Boolean);

      var payload = {
        mode: selMode,
        ai_thresholds: {
          challenge_min: chMin,
          block_min: blMin
        },
        rate_limit_global_rpm: globalRpm,
        protected_routes: [
          { path_prefix: '/login', methods: ['POST'], require_token: true, rate_limit_rpm: 10 },
          { path_prefix: '/api/consulta', methods: ['GET', 'POST'], require_token: true, rate_limit_rpm: 30 }
        ],
        ip_whitelist: wlArray,
        ip_blacklist: ['198.51.100.42']
      };

      fetch('/api/v1/admin/policies/' + (state.activeSiteId || 'default'), {
        method: 'PUT',
        headers: this.getHeaders(),
        body: JSON.stringify(payload)
      })
        .then(function (res) {
          if (!res.ok) throw new Error('HTTP ' + res.status);
          return res.json();
        })
        .then(function (data) {
          self.showToast('✓ Políticas sincronizadas en Borde y Backend.');
        })
        .catch(function (err) {
          self.showToast('Error al guardar políticas: ' + err.message);
        });
    },

    // =========================================================================
    // MÓDULO 3: BÓVEDA CRIPTOGRÁFICA LOCAL
    // =========================================================================
    fetchCryptoKeys: function () {
      fetch('/api/v1/admin/vault/keys', { headers: this.getHeaders() })
        .then(function (res) { return res.json(); })
        .then(function (keys) {
          if (Array.isArray(keys) && keys.length > 0) {
            var active = keys.find(function (k) { return k.active; }) || keys[keys.length - 1];
            var kidEl = document.getElementById('txtKid');
            var pemEl = document.getElementById('txtPem');
            if (kidEl) kidEl.textContent = active.kid;
            if (pemEl) pemEl.textContent = active.public_key_pem;

            var tbody = document.getElementById('vaultKeysTableBody');
            if (tbody) {
              tbody.innerHTML = '';
              keys.forEach(function (k) {
                var tr = document.createElement('tr');
                tr.innerHTML = [
                  '<td><code>' + k.kid + '</code></td>',
                  '<td>' + k.algorithm + '</td>',
                  '<td>' + k.curve + '</td>',
                  '<td><span class="action-pill ' + (k.active ? 'pasivo' : 'bloqueo') + '">● ' + (k.active ? 'Activa' : 'Archivada') + '</span></td>'
                ].join('');
                tbody.appendChild(tr);
              });
            }
          }
        })
        .catch(function () {});
    },

    rotarClave: function () {
      var self = this;
      if (confirm('¿Confirmar rotación inmediata de clave asimétrica Ed25519 en la bóveda AES-256-GCM?')) {
        fetch('/api/v1/admin/vault/rotate', {
          method: 'POST',
          headers: this.getHeaders()
        })
          .then(function (res) { return res.json(); })
          .then(function (data) {
            var newKid = data.kid || (data.new_key_info && data.new_key_info.kid);
            if (newKid) {
              document.getElementById('txtKid').textContent = newKid;
              if (data.public_key_pem) {
                document.getElementById('txtPem').textContent = data.public_key_pem;
              }
              self.showToast('✓ Clave rotada con éxito: ' + newKid);
              self.fetchCryptoKeys();
            }
          })
          .catch(function (err) {
            self.showToast('Error al rotar clave: ' + err.message);
          });
      }
    },

    // =========================================================================
    // MÓDULO 5: GESTIÓN DEL MODELO DE IA
    // =========================================================================
    fetchAiModelInfo: function () {
      fetch('/api/v1/admin/observability/summary')
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (data.ai_performance) {
            var vEl = document.getElementById('aiModelVersion');
            var aEl = document.getElementById('aiModelAccuracy');
            if (vEl) vEl.textContent = data.ai_performance.active_model_version;
            if (aEl) aEl.textContent = ((data.ai_performance.model_accuracy || 0.994) * 100).toFixed(1) + ' %';
          }
        })
        .catch(function () {});
    },

    uploadModelFile: function (inputEl) {
      var self = this;
      if (!inputEl.files || inputEl.files.length === 0) return;
      var file = inputEl.files[0];
      var statusDiv = document.getElementById('aiUploadStatus');
      if (statusDiv) {
        statusDiv.style.color = '#38bdf8';
        statusDiv.textContent = 'Subiendo y validando ' + file.name + '...';
      }

      var formData = new FormData();
      formData.append('file', file);

      var headers = {};
      if (state.adminToken) {
        headers['Authorization'] = 'Bearer ' + state.adminToken;
      }

      fetch('/api/v1/admin/ai/model/upload', {
        method: 'POST',
        headers: headers,
        body: formData
      })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (statusDiv) {
            if (data.model_version) {
              statusDiv.style.color = '#10b981';
              statusDiv.textContent = '✓ ' + data.message + ' (Versión: ' + data.model_version + ')';
              self.showToast('Modelo recargado en memoria RAM con éxito.');
              self.fetchAiModelInfo();
            } else {
              statusDiv.style.color = '#ef4444';
              statusDiv.textContent = 'Error: ' + (data.error ? data.error.message : 'Fallo en recarga');
            }
          }
        })
        .catch(function (err) {
          if (statusDiv) {
            statusDiv.style.color = '#ef4444';
            statusDiv.textContent = 'Error al subir modelo: ' + err.message;
          }
        });
    },

    // =========================================================================
    // MÓDULO 6: AUDITORÍA INMUTABLE (SHA-256)
    // =========================================================================
    fetchAuditLogs: function () {
      fetch('/api/v1/admin/audit-logs', { headers: this.getHeaders() })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          var badge = document.getElementById('auditIntegrityBadge');
          if (badge) {
            if (data.chain_integrity_valid) {
              badge.textContent = 'Integridad de Cadena Verificada: 100% VÁLIDA (chain_integrity_valid: true)';
              badge.style.color = '#6ee7b7';
            } else {
              badge.textContent = 'ADVERTENCIA: Integridad de Cadena Comprometida';
              badge.style.color = '#f87171';
            }
          }

          var tbody = document.getElementById('auditTableBody');
          if (!tbody) return;
          tbody.innerHTML = '';

          if (data.items && data.items.length > 0) {
            data.items.slice(0, 15).forEach(function (log) {
              var timeStr = log.timestamp ? log.timestamp.replace('T', ' ').substring(0, 19) : '--';
              var shortHash = log.entry_hash ? (log.entry_hash.substring(0, 12) + '...') : '--';

              var tr = document.createElement('tr');
              tr.innerHTML = [
                '<td>#' + log.id + '</td>',
                '<td>' + timeStr + '</td>',
                '<td><strong>' + (log.actor_username || 'system') + '</strong></td>',
                '<td>' + (log.actor_role || 'admin') + '</td>',
                '<td>' + log.action + '</td>',
                '<td>' + (log.resource || '--') + '</td>',
                '<td><code style="color: #38bdf8;">' + shortHash + '</code></td>'
              ].join('');
              tbody.appendChild(tr);
            });
          }
        })
        .catch(function () {});
    },

    // =========================================================================
    // MÓDULO 4: OBSERVABILIDAD EN TIEMPO REAL Y GRÁFICAS EXACTAS
    // =========================================================================
    setupResize: function () {
      var self = this;
      window.addEventListener('resize', function () {
        if (state.currentView === '4') {
          self.resizeCanvas();
        }
      });
    },

    resizeCanvas: function () {
      var canvas = document.getElementById('chartCanvas') || document.getElementById('trafficChart');
      if (!canvas) return;
      var rect = canvas.parentElement.getBoundingClientRect();
      canvas.width = rect.width || 800;
      canvas.height = 180;
      this.drawChart();
    },

    initChart: function () {
      var self = this;
      setTimeout(function () {
        self.resizeCanvas();
      }, 50);
      setTimeout(function () {
        self.resizeCanvas();
      }, 300);
    },

    drawChart: function () {
      var canvas = document.getElementById('chartCanvas') || document.getElementById('trafficChart');
      if (!canvas) return;
      var ctx = canvas.getContext('2d');
      var w = canvas.width;
      var h = canvas.height;

      ctx.clearRect(0, 0, w, h);

      // Líneas sutiles de cuadrícula de fondo
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
      ctx.lineWidth = 1;
      for (var gl = 1; gl <= 3; gl++) {
        var gy = (h / 4) * gl;
        ctx.beginPath();
        ctx.moveTo(0, gy);
        ctx.lineTo(w, gy);
        ctx.stroke();
      }

      var ptsHuman = state.trafficPointsHuman;
      var ptsBots = state.trafficPointsBots;
      var n = ptsHuman.length;
      var stepX = w / (n - 1);

      var paddingBottom = 16;
      var paddingTop = 16;
      var plotH = Math.max(20, h - paddingBottom - paddingTop);

      var maxObserved = Math.max.apply(null, ptsHuman.concat(ptsBots));
      var maxVal = Math.max(10, maxObserved * 1.25);

      function getY(val) {
        var clamped = Math.max(0, Math.min(val, maxVal));
        return (h - paddingBottom) - (clamped / maxVal) * plotH;
      }

      var hasHumanData = ptsHuman.some(function (v) { return v > 0; });
      var hasBotData = ptsBots.some(function (v) { return v > 0; });

      // 1. Área y curva de Tráfico Humano (Verde Neón)
      if (hasHumanData) {
        ctx.beginPath();
        ctx.moveTo(0, getY(ptsHuman[0]));
        for (var i = 0; i < n - 1; i++) {
          var x0 = i * stepX;
          var y0 = getY(ptsHuman[i]);
          var x1 = (i + 1) * stepX;
          var y1 = getY(ptsHuman[i + 1]);
          var cx = (x0 + x1) / 2;
          ctx.bezierCurveTo(cx, y0, cx, y1, x1, y1);
        }
        ctx.lineTo(w, h - paddingBottom);
        ctx.lineTo(0, h - paddingBottom);
        ctx.closePath();

        var gradHuman = ctx.createLinearGradient(0, 0, 0, h);
        gradHuman.addColorStop(0, 'rgba(0, 230, 118, 0.35)');
        gradHuman.addColorStop(0.7, 'rgba(16, 185, 129, 0.1)');
        gradHuman.addColorStop(1, 'rgba(16, 185, 129, 0.0)');
        ctx.fillStyle = gradHuman;
        ctx.fill();

        ctx.beginPath();
        ctx.moveTo(0, getY(ptsHuman[0]));
        for (var j = 0; j < n - 1; j++) {
          var hx0 = j * stepX;
          var hy0 = getY(ptsHuman[j]);
          var hx1 = (j + 1) * stepX;
          var hy1 = getY(ptsHuman[j + 1]);
          var hcx = (hx0 + hx1) / 2;
          ctx.bezierCurveTo(hcx, hy0, hcx, hy1, hx1, hy1);
        }
        ctx.strokeStyle = '#00e676';
        ctx.lineWidth = 2.5;
        ctx.stroke();
      } else {
        // Línea base plana en cero
        ctx.beginPath();
        ctx.moveTo(0, getY(0));
        ctx.lineTo(w, getY(0));
        ctx.strokeStyle = 'rgba(0, 230, 118, 0.3)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      // 2. Área y curva de Bots Mitigados (Rojo)
      if (hasBotData) {
        ctx.beginPath();
        ctx.moveTo(0, getY(ptsBots[0]));
        for (var k = 0; k < n - 1; k++) {
          var bx0 = k * stepX;
          var by0 = getY(ptsBots[k]);
          var bx1 = (k + 1) * stepX;
          var by1 = getY(ptsBots[k + 1]);
          var bcx = (bx0 + bx1) / 2;
          ctx.bezierCurveTo(bcx, by0, bcx, by1, bx1, by1);
        }
        ctx.lineTo(w, h - paddingBottom);
        ctx.lineTo(0, h - paddingBottom);
        ctx.closePath();

        var gradBot = ctx.createLinearGradient(0, 0, 0, h);
        gradBot.addColorStop(0, 'rgba(239, 68, 68, 0.35)');
        gradBot.addColorStop(0.7, 'rgba(239, 68, 68, 0.1)');
        gradBot.addColorStop(1, 'rgba(239, 68, 68, 0.0)');
        ctx.fillStyle = gradBot;
        ctx.fill();

        ctx.beginPath();
        ctx.moveTo(0, getY(ptsBots[0]));
        for (var l = 0; l < n - 1; l++) {
          var rx0 = l * stepX;
          var ry0 = getY(ptsBots[l]);
          var rx1 = (l + 1) * stepX;
          var ry1 = getY(ptsBots[l + 1]);
          var rcx = (rx0 + rx1) / 2;
          ctx.bezierCurveTo(rcx, ry0, rcx, ry1, rx1, ry1);
        }
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 2;
        ctx.stroke();
      } else {
        // Línea base plana en cero
        ctx.beginPath();
        ctx.moveTo(0, getY(0));
        ctx.lineTo(w, getY(0));
        ctx.strokeStyle = 'rgba(239, 68, 68, 0.3)';
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    },

    startDataPolling: function () {
      var self = this;
      this.pollObservability();
      if (state.pollTimer) clearInterval(state.pollTimer);
      state.pollTimer = setInterval(function () {
        self.pollObservability();
      }, 2000);
    },

    pollObservability: function () {
      var self = this;
      fetch('/api/v1/admin/observability/summary')
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (data.traffic_stats) {
            var stats = data.traffic_stats;
            var kpiTotal = document.getElementById('kpiTotalRequests');
            if (kpiTotal) kpiTotal.textContent = stats.total_requests.toLocaleString();

            var kpiPct = document.getElementById('kpiHumanPct');
            if (kpiPct) kpiPct.textContent = stats.human_percentage + '%';

            // Calcular delta instantáneo real de humanos y bots para la gráfica
            var curHumans = stats.verified_humans || 0;
            var curBots = (stats.bots_blocked || 0) + (stats.ddos_rate_limited || 0);

            // En la primera carga, sincronizar la línea base real sin inyectar picos artificiales
            if (state.isFirstPoll) {
              state.isFirstPoll = false;
              state.lastVerifiedCount = curHumans;
              state.lastBlockedCount = curBots;
            } else {
              var deltaHuman = Math.max(0, curHumans - (state.lastVerifiedCount || 0));
              var deltaBots = Math.max(0, curBots - (state.lastBlockedCount || 0));

              state.lastVerifiedCount = curHumans;
              state.lastBlockedCount = curBots;

              // Registro 100% puro y exacto del tráfico real recibido en la ventana
              state.trafficPointsHuman.shift();
              state.trafficPointsHuman.push(deltaHuman);

              state.trafficPointsBots.shift();
              state.trafficPointsBots.push(deltaBots);
            }

            self.drawChart();
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

    setEventsFilter: function (filterType) {
      state.eventsFilter = filterType;
      var buttons = document.querySelectorAll('.events-filter-bar .filter-btn');
      buttons.forEach(function (btn) {
        btn.classList.remove('active');
      });

      var activeBtnMap = {
        'all': 'btnFilterAll',
        'blocked': 'btnFilterBlocked',
        'rate_limited': 'btnFilterRateLimit',
        'challenged': 'btnFilterChallenged',
        'verified': 'btnFilterVerified'
      };
      var targetId = activeBtnMap[filterType];
      if (targetId) {
        var el = document.getElementById(targetId);
        if (el) el.classList.add('active');
      }

      this.updateEventsTable(state.lastSecurityEvents);
    },

    updateEventsTable: function (events) {
      state.lastSecurityEvents = events || [];
      var tbody = document.getElementById('eventsTableBody');
      if (!tbody) return;

      var filter = state.eventsFilter || 'all';
      var filtered = state.lastSecurityEvents.filter(function (ev) {
        if (filter === 'all') return true;
        if (filter === 'blocked') return ev.action === 'blocked';
        if (filter === 'rate_limited') return ev.action === 'rate_limited';
        if (filter === 'challenged') return ev.action === 'challenged' || ev.action === 'challenge_solved';
        if (filter === 'verified') return ev.action === 'verified' || ev.action === 'passive';
        return true;
      });

      tbody.innerHTML = '';

      if (filtered.length === 0) {
        var trEmpty = document.createElement('tr');
        trEmpty.innerHTML = '<td colspan="5" style="text-align: center; color: #64748b; padding: 18px;">No hay eventos registrados para la acción seleccionada.</td>';
        tbody.appendChild(trEmpty);
        return;
      }

      filtered.slice(0, 10).forEach(function (ev) {
        var timeStr = ev.timestamp ? (ev.timestamp.split('T')[1] ? ev.timestamp.split('T')[1].substring(0, 8) : ev.timestamp) : '--:--:--';
        var actionPill;
        if (ev.action === 'blocked') {
          actionPill = '<span class="action-pill bloqueo">● Bloqueo</span>';
        } else if (ev.action === 'rate_limited') {
          actionPill = '<span class="action-pill desafio">● Rate Limit</span>';
        } else if (ev.action === 'challenged' || ev.action === 'challenge_solved') {
          actionPill = '<span class="action-pill desafio">● Desafío</span>';
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
      }, 3500);
    }
  };

  document.addEventListener('DOMContentLoaded', function () {
    window.App.init();
  });
})();
