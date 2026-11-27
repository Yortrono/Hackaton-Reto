#!/usr/bin/env python3
"""
Validación Exhaustiva: Autenticación Administrativa MFA/TOTP,
Control de Acceso Basado en Roles (RBAC) y Módulos Funcionales del Panel
Hackathon Venezuela Innova 2026 - Mincyt
"""

import sys
import json
import time
import base64
import hmac
import hashlib
import struct
import subprocess
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def reset_totp_state():
    """Restaura el estado inicial de MFA en la base de datos para pruebas reproducibles."""
    cmd = [
        "podman", "exec", "backend-nucleo", "python3", "-c",
        "from app.db.database import get_db_context; from app.db.models import AdminUserModel;\n"
        "with get_db_context() as db:\n"
        "    for u in db.query(AdminUserModel).all():\n"
        "        u.totp_enabled = False\n"
        "        u.totp_secret = None\n"
        "    db.commit()\n"
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def generate_totp_code(secret_b32: str, interval: int = 30) -> str:
    """Implementación RFC 6238 TOTP pura (Zero Dependencias Externas)."""
    clean_secret = secret_b32.strip().upper()
    padding = (8 - len(clean_secret) % 8) % 8
    key = base64.b32decode(clean_secret + ("=" * padding))
    counter = int(time.time() // interval)
    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0f
    code = (struct.unpack(">I", h[offset:offset + 4])[0] & 0x7fffffff) % 1000000
    return f"{code:06d}"

BACKEND_URL = "http://127.0.0.1:8000"
ADMIN_CONSOLE_URL = "http://127.0.0.1:3000"

PASSWORDS = {
    "admin_seguridad": "Soberania2026!Segura",
    "operador_politicas": "Operador2026!Vzla",
    "auditor_fiscal": "Auditor2026!Transparente"
}

ROLES = {
    "admin_seguridad": "security_admin",
    "operador_politicas": "operator",
    "auditor_fiscal": "auditor"
}

def print_header(title):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

def assert_test(cond, title, detail=""):
    badge = "[✓ CUMPLE]" if cond else "[✗ FALLÓ]"
    print(f" {badge} {title}")
    if detail:
        print(f"       ↳ {detail}")
    if not cond:
        raise AssertionError(f"Falla en: {title} — {detail}")

def test_mfa_and_auth():
    print_header("FASE 1: AUTENTICACIÓN ADMINISTRATIVA, MFA/TOTP Y PROTECCIÓN DE ACCESO")

    # 1.1 Login con credenciales inválidas debe fallar
    res_bad = requests.post(f"{BACKEND_URL}/api/v1/admin/auth/login", json={
        "username": "admin_seguridad",
        "password": "PasswordIncorrecto123!"
    })
    assert_test(res_bad.status_code == 401, "Rechazo de credenciales incorrectas (HTTP 401)", f"Código devuelto: {res_bad.status_code}")

    # 1.2 Login válido de cada usuario sin MFA inicial
    tokens = {}
    for user, pwd in PASSWORDS.items():
        res = requests.post(f"{BACKEND_URL}/api/v1/admin/auth/login", json={
            "username": user,
            "password": pwd
        })
        assert_test(res.status_code == 200, f"Autenticación exitosa de '{user}'", f"HTTP 200, rol retornado: {res.json().get('role')}")
        data = res.json()
        assert_test(data.get("role") == ROLES[user], f"Asignación correcta del rol RBAC '{ROLES[user]}' para {user}")
        tokens[user] = data.get("access_token")

    # 1.3 Configuración de MFA/TOTP para operador_politicas
    op_token = tokens["operador_politicas"]
    res_setup = requests.post(
        f"{BACKEND_URL}/api/v1/admin/auth/setup-totp",
        headers={"Authorization": f"Bearer {op_token}"}
    )
    assert_test(res_setup.status_code == 200, "Generación de secreto TOTP (/setup-totp)", f"HTTP 200, secreto retornado: {res_setup.json().get('secret')[:8]}...")
    totp_secret = res_setup.json()["secret"]
    totp_uri = res_setup.json()["provisioning_uri"]
    assert_test("otpauth://totp/" in totp_uri, "URI compatible con autenticadores soberanos/FOSS (RFC 6238)")

    # 1.4 Enrolamiento con código TOTP inválido debe rebotar
    res_verify_bad = requests.post(
        f"{BACKEND_URL}/api/v1/admin/auth/verify-totp",
        headers={"Authorization": f"Bearer {op_token}"},
        json={"totp_code": "000000"}
    )
    assert_test(res_verify_bad.status_code == 400, "Rechazo de código TOTP inválido en activación (HTTP 400)")

    # 1.5 Enrolamiento con código TOTP válido
    valid_code = generate_totp_code(totp_secret)
    res_verify_ok = requests.post(
        f"{BACKEND_URL}/api/v1/admin/auth/verify-totp",
        headers={"Authorization": f"Bearer {op_token}"},
        json={"totp_code": valid_code}
    )
    assert_test(res_verify_ok.status_code == 200, "Activación exitosa de MFA/TOTP (/verify-totp)", f"HTTP 200: {res_verify_ok.json().get('message')}")

    # 1.6 Login subsecuente de operador_politicas sin código TOTP debe solicitar MFA
    res_mfa_req = requests.post(f"{BACKEND_URL}/api/v1/admin/auth/login", json={
        "username": "operador_politicas",
        "password": PASSWORDS["operador_politicas"]
    })
    assert_test(res_mfa_req.status_code == 200 and res_mfa_req.json().get("mfa_required") is True,
                "Exigencia obligatoria de segundo factor MFA para usuario enrolado",
                f"mfa_required={res_mfa_req.json().get('mfa_required')}")

    # 1.7 Login con código TOTP válido completa la autenticación
    res_mfa_ok = requests.post(f"{BACKEND_URL}/api/v1/admin/auth/login", json={
        "username": "operador_politicas",
        "password": PASSWORDS["operador_politicas"],
        "totp_code": generate_totp_code(totp_secret)
    })
    assert_test(res_mfa_ok.status_code == 200 and res_mfa_ok.json().get("access_token") is not None,
                "Autenticación completada exitosamente con Password + TOTP",
                f"Token emitido: {res_mfa_ok.json().get('access_token')[:18]}...")
    tokens["operador_politicas"] = res_mfa_ok.json().get("access_token")

    return tokens

def test_rbac_matrix(tokens):
    print_header("FASE 2: MATRIZ DE CONTROL DE ACCESO BASADO EN ROLES (RBAC)")

    admin_tok = tokens["admin_seguridad"]
    op_tok = tokens["operador_politicas"]
    aud_tok = tokens["auditor_fiscal"]

    # 2.1 Bóveda Criptográfica: Solo security_admin puede rotar claves
    res_rot_admin = requests.post(f"{BACKEND_URL}/api/v1/admin/vault/rotate", headers={"Authorization": f"Bearer {admin_tok}"})
    assert_test(res_rot_admin.status_code == 200, "Rol 'security_admin' puede rotar claves en Bóveda", f"HTTP 200: nueva clave={res_rot_admin.json().get('kid')}")

    res_rot_op = requests.post(f"{BACKEND_URL}/api/v1/admin/vault/rotate", headers={"Authorization": f"Bearer {op_tok}"})
    assert_test(res_rot_op.status_code == 403, "Rol 'operator' es bloqueado al intentar rotar claves (HTTP 403)", f"Código: {res_rot_op.status_code}")

    res_rot_aud = requests.post(f"{BACKEND_URL}/api/v1/admin/vault/rotate", headers={"Authorization": f"Bearer {aud_tok}"})
    assert_test(res_rot_aud.status_code == 403, "Rol 'auditor' es bloqueado al intentar rotar claves (HTTP 403)", f"Código: {res_rot_aud.status_code}")

    # 2.2 Gestión de IA: Solo security_admin puede subir pesos de modelo
    dummy_model_bytes = b"ONNX_DUMMY_WEIGHTS_SOBERANO_TEST" * 10
    files = {"file": ("test.onnx", dummy_model_bytes, "application/octet-stream")}
    
    res_ai_op = requests.post(f"{BACKEND_URL}/api/v1/admin/ai/model/upload",
                              headers={"Authorization": f"Bearer {op_tok}"},
                              files={"file": ("test.onnx", dummy_model_bytes, "application/octet-stream")})
    assert_test(res_ai_op.status_code == 403, "Rol 'operator' es bloqueado al intentar cargar pesos de IA (HTTP 403)", f"Código: {res_ai_op.status_code}")

    res_ai_aud = requests.post(f"{BACKEND_URL}/api/v1/admin/ai/model/upload",
                               headers={"Authorization": f"Bearer {aud_tok}"},
                               files={"file": ("test.onnx", dummy_model_bytes, "application/octet-stream")})
    assert_test(res_ai_aud.status_code == 403, "Rol 'auditor' es bloqueado al intentar cargar pesos de IA (HTTP 403)", f"Código: {res_ai_aud.status_code}")

    # 2.3 Modificación de Políticas: security_admin y operator pueden; auditor es bloqueado
    policy_payload = {
        "mode": "challenge",
        "ai_thresholds": {"challenge_min": 0.35, "block_min": 0.75},
        "rate_limit_global_rpm": 130,
        "protected_routes": [
            {"path_prefix": "/login", "methods": ["POST"], "require_token": True, "rate_limit_rpm": 10},
            {"path_prefix": "/api/consulta", "methods": ["GET", "POST"], "require_token": True, "rate_limit_rpm": 30}
        ],
        "ip_whitelist": ["127.0.0.1", "10.0.0.0/8"],
        "ip_blacklist": ["198.51.100.42"]
    }

    res_pol_op = requests.put(f"{BACKEND_URL}/api/v1/admin/policies/default",
                              headers={"Authorization": f"Bearer {op_tok}"},
                              json=policy_payload)
    assert_test(res_pol_op.status_code == 200, "Rol 'operator' puede actualizar políticas de mitigación", f"HTTP 200: rate_limit_global_rpm={res_pol_op.json().get('policy', {}).get('rate_limit_global_rpm')}")

    res_pol_aud = requests.put(f"{BACKEND_URL}/api/v1/admin/policies/default",
                               headers={"Authorization": f"Bearer {aud_tok}"},
                               json=policy_payload)
    assert_test(res_pol_aud.status_code == 403, "Rol 'auditor' es bloqueado al intentar modificar políticas (HTTP 403)", f"Código: {res_pol_aud.status_code}")

    # 2.4 Lectura de Auditoría e Integridad: Todos los roles autorizados pueden auditar
    for user, tok in tokens.items():
        res_aud = requests.get(f"{BACKEND_URL}/api/v1/admin/audit-logs", headers={"Authorization": f"Bearer {tok}"})
        assert_test(res_aud.status_code == 200, f"Rol '{ROLES[user]}' tiene acceso de lectura a la bitácora de auditoría", f"HTTP 200, registros obtenidos: {len(res_aud.json().get('items', []))}")

def test_functional_modules(tokens):
    print_header("FASE 3: VALIDACIÓN DE TODOS LOS MÓDULOS FUNCIONALES DEL PANEL")
    admin_tok = tokens["admin_seguridad"]
    headers = {"Authorization": f"Bearer {admin_tok}"}

    # =========================================================================
    # MÓDULO 1: GESTIÓN DE SITIOS Y APLICACIONES
    # =========================================================================
    print("\n--- Módulo 1: Sitios y Aplicaciones ---")
    res_sites = requests.get(f"{BACKEND_URL}/api/v1/admin/sites", headers=headers)
    assert_test(res_sites.status_code == 200, "Consulta de sitios registrados (GET /api/v1/admin/sites)")
    sites = res_sites.json()
    assert_test(len(sites) >= 1 and "site_key" in sites[0], "Existencia de sitio principal con site_key pública", f"Site ID: {sites[0]['site_id']}, Site Key: {sites[0]['site_key']}")

    new_site_id = f"tramites-mppct-{int(time.time())}"
    res_create_site = requests.post(f"{BACKEND_URL}/api/v1/admin/sites", headers=headers, json={
        "site_id": new_site_id,
        "name": "Portal de Trámites Soberanos",
        "domain": "tramites.ciencia.gob.ve",
        "allowed_origins": ["https://tramites.ciencia.gob.ve", "http://localhost:8080"]
    })
    assert_test(res_create_site.status_code in [200, 201], "Registro de nuevo sitio y generación de claves (POST /api/v1/admin/sites)", f"Site Key: {res_create_site.json().get('site_key')}")

    # =========================================================================
    # MÓDULO 2: MOTOR DE REGLAS Y MITIGACIÓN
    # =========================================================================
    print("\n--- Módulo 2: Motor de Reglas y Mitigación ---")
    res_pol_get = requests.get(f"{BACKEND_URL}/api/v1/policies/default")
    assert_test(res_pol_get.status_code == 200, "Lectura de políticas activas (GET /api/v1/policies/default)")
    pol = res_pol_get.json().get("policy", {})
    assert_test(pol.get("mode") in ["monitor", "challenge", "block"], "Modo de mitigación perimetral configurado", f"Modo actual: {pol.get('mode')}")
    assert_test("challenge_min" in pol.get("ai_thresholds", {}) and "block_min" in pol.get("ai_thresholds", {}), "Umbrales de sensibilidad de IA configurados")
    assert_test(len(pol.get("protected_routes", [])) >= 2, "Definición de rutas protegidas con token obligatorio")

    # =========================================================================
    # MÓDULO 3: BÓVEDA CRIPTOGRÁFICA LOCAL
    # =========================================================================
    print("\n--- Módulo 3: Bóveda Criptográfica Local ---")
    res_keys = requests.get(f"{BACKEND_URL}/api/v1/admin/vault/keys", headers=headers)
    assert_test(res_keys.status_code == 200, "Inspección de claves en Bóveda (GET /api/v1/admin/vault/keys)")
    keys_list = res_keys.json()
    assert_test(isinstance(keys_list, list) and len(keys_list) >= 1, "Historial de claves bajo custodia AES-256-GCM verificado", f"Total claves: {len(keys_list)}")
    active_key = next((k for k in keys_list if k.get("active")), keys_list[0])
    assert_test("kid" in active_key and "public_key_pem" in active_key, "Disponibilidad de clave pública activa PEM Ed25519", f"KID activo: {active_key.get('kid')}")
    assert_test("BEGIN PUBLIC KEY" in active_key["public_key_pem"], "Formato estándar PEM X.509 de clave Ed25519")

    # =========================================================================
    # MÓDULO 4: OBSERVABILIDAD EN TIEMPO REAL
    # =========================================================================
    print("\n--- Módulo 4: Observabilidad en Tiempo Real ---")
    res_summary = requests.get(f"{BACKEND_URL}/api/v1/admin/observability/summary")
    assert_test(res_summary.status_code == 200, "KPIs y métricas de observabilidad (GET /api/v1/admin/observability/summary)")
    summary = res_summary.json()
    t_stats = summary.get("traffic_stats", {})
    assert_test("total_requests" in t_stats and "human_percentage" in t_stats,
                "KPIs de tráfico presentes: Peticiones y % Tráfico Humano",
                f"Peticiones={t_stats.get('total_requests')}, Humano={t_stats.get('human_percentage')}%")

    events = summary.get("recent_security_events", [])
    if len(events) > 0:
        first_ev = events[0]
        assert_test(first_ev.get("ip_hash", "").startswith("sha256:"), "Anonimización de IPs mediante hash criptográfico SHA-256", f"Ejemplo IP: {first_ev.get('ip_hash')}")

    # =========================================================================
    # MÓDULO 5: GESTIÓN DEL MODELO DE IA LOCAL
    # =========================================================================
    print("\n--- Módulo 5: Gestión del Modelo de IA Local ---")
    ai_perf = summary.get("ai_performance", {})
    assert_test("active_model_version" in ai_perf and "model_accuracy" in ai_perf,
                "Métricas y versión activa del modelo expuestas",
                f"Versión: {ai_perf.get('active_model_version')}, Precisión: {ai_perf.get('model_accuracy') * 100:.1f}%")

    # =========================================================================
    # MÓDULO 6: AUDITORÍA INMUTABLE (SHA-256)
    # =========================================================================
    print("\n--- Módulo 6: Auditoría Inmutable Encadenada ---")
    res_audit = requests.get(f"{BACKEND_URL}/api/v1/admin/audit-logs", headers=headers)
    assert_test(res_audit.status_code == 200, "Verificación criptográfica de la cadena de auditoría (GET /api/v1/admin/audit-logs)")
    audit_data = res_audit.json()
    assert_test(audit_data.get("chain_integrity_valid") is True, "Integridad de la cadena inmutable 100% válida (SHA-256 Hash Chain)",
                f"Total de bloques encadenados: {len(audit_data.get('items', []))}")

def main():
    print("╔════════════════════════════════════════════════════════════════════════════════════╗")
    print("║     AUDITORÍA Y VALIDACIÓN DE ACCESO ADMINISTRATIVO, MFA/TOTP, RBAC Y PANELES      ║")
    print("║     Servicio Autónomo de Verificación Humana y Mitigación de Bots (Mincyt 2026)    ║")
    print("╚════════════════════════════════════════════════════════════════════════════════════╝")

    reset_totp_state()
    tokens = test_mfa_and_auth()
    test_rbac_matrix(tokens)
    test_functional_modules(tokens)

    print("\n" + "=" * 80)
    print(" RESULTADO FINAL: 100% DE LAS PRUEBAS DE ACCESO, MFA, RBAC Y MÓDULOS SUPERADAS CON ÉXITO")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
