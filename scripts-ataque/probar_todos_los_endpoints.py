#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Verificación Integral de Endpoints Soberanos
Hackathon Venezuela Innova 2026 — Servicio Autónomo de Verificación Humana y Mitigación de Bots

Este script audita y valida sistemáticamente todos los endpoints expuestos
por la arquitectura integral 100 % on-premise / air-gapped:
  1. Borde Perimetral TLS 1.3 (OpenResty + Lua / Puerto 8443 y 8088)
  2. Backend Núcleo Soberano (FastAPI / Puerto 8000)
  3. Motor de Inferencia IA Conductual (LightGBM/ONNX / Puerto 8001)
  4. Consola Administrativa y Observabilidad (Node.js / Puerto 3000)
  5. Aplicación Institucional Protegida (Demo Ciudadana)
"""

import sys
import time
import json
import uuid
import hashlib
from typing import Dict, Any, Optional, Tuple, List
import requests
import urllib3

# Deshabilitar advertencias TLS por certificado autofirmado soberano local
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuración de URLs base para cada microservicio
BORDE_URL = "https://localhost:8443"
BORDE_HTTP_URL = "http://localhost:8088"
BACKEND_URL = "http://localhost:8000"
IA_URL = "http://localhost:8001"
CONSOLA_URL = "http://localhost:3000"

# Códigos de escape ANSI para formato en terminal
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
GRAY = "\033[90m"

class EndpointTester:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.verify = False
        self.admin_token: Optional[str] = None
        self.human_token: Optional[str] = None
        self.results: List[Dict[str, Any]] = []

    def log_header(self, title: str) -> None:
        print(f"\n{BOLD}{CYAN}══════════════════════════════════════════════════════════════════════════════════{RESET}")
        print(f"{BOLD}{CYAN}  {title}{RESET}")
        print(f"{BOLD}{CYAN}══════════════════════════════════════════════════════════════════════════════════{RESET}")

    def resolver_pow(self, nonce: str, difficulty: int) -> str:
        """Resuelve el Proof-of-Work criptográfico SHA-256 localmente."""
        target_prefix = "0" * difficulty
        counter = 0
        while True:
            sol_hex = hex(counter)[2:]
            digest = hashlib.sha256(f"{nonce}{sol_hex}".encode("utf-8")).hexdigest()
            if digest.startswith(target_prefix):
                return sol_hex
            counter += 1
            if counter > 500000:
                raise RuntimeError("Límite de iteraciones PoW alcanzado")

    def registrar_resultado(
        self,
        modulo: str,
        metodo: str,
        ruta: str,
        status_esperado: int,
        status_obtenido: int,
        latencia_ms: float,
        detalle: str = ""
    ) -> bool:
        exito = (status_obtenido == status_esperado)
        icono = f"{GREEN}✓ PASÓ{RESET}" if exito else f"{RED}✕ FALLÓ{RESET}"
        
        self.results.append({
            "modulo": modulo,
            "metodo": metodo,
            "ruta": ruta,
            "esperado": status_esperado,
            "obtenido": status_obtenido,
            "latencia_ms": latencia_ms,
            "exito": exito,
            "detalle": detalle
        })

        color_status = GREEN if exito else RED
        print(f" {icono} {BOLD}{metodo:<6}{RESET} {ruta:<42} | HTTP {color_status}{status_obtenido}{RESET} (esp {status_esperado}) | {latencia_ms:6.1f} ms {GRAY}{detalle}{RESET}")
        return exito

    def ejecutar_test(
        self,
        modulo: str,
        metodo: str,
        url_completa: str,
        ruta_display: str,
        status_esperado: int,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        allow_redirects: bool = True
    ) -> Tuple[int, Any, float]:
        t0 = time.time()
        try:
            resp = self.session.request(
                method=metodo,
                url=url_completa,
                headers=headers or {},
                json=json_data,
                allow_redirects=allow_redirects,
                timeout=5.0
            )
            latencia_ms = (time.time() - t0) * 1000.0
            try:
                data = resp.json()
            except Exception:
                data = resp.text

            self.registrar_resultado(
                modulo=modulo,
                metodo=metodo,
                ruta=ruta_display,
                status_esperado=status_esperado,
                status_obtenido=resp.status_code,
                latencia_ms=latencia_ms
            )
            return resp.status_code, data, latencia_ms
        except Exception as e:
            latencia_ms = (time.time() - t0) * 1000.0
            self.registrar_resultado(
                modulo=modulo,
                metodo=metodo,
                ruta=ruta_display,
                status_esperado=status_esperado,
                status_obtenido=0,
                latencia_ms=latencia_ms,
                detalle=f"Excepción: {str(e)[:30]}"
            )
            return 0, None, latencia_ms

    # =========================================================================
    # 1. MOTOR DE IA CONDUCTUAL (PUERTO 8001)
    # =========================================================================
    def probar_ia_conductual(self) -> None:
        self.log_header("MÓDULO IA CONDUCTUAL (Local en RAM — Puerto 8001)")

        # 1.1 Health
        self.ejecutar_test("IA", "GET", f"{IA_URL}/health", "/health", 200)

        # 1.2 Métricas internas
        self.ejecutar_test("IA", "GET", f"{IA_URL}/internal/metrics", "/internal/metrics", 200)

        # 1.3 Inferencia de telemetría Humana (Debe clasificar human, latencia < 50ms)
        payload_humano = {
            "challenge_id": str(uuid.uuid4()),
            "telemetry_window_ms": 2300,
            "pointer_metrics": {
                "event_count": 48,
                "mean_velocity": 1.25,
                "std_acceleration": 0.45,
                "angular_entropy": 2.82,
                "straight_line_ratio": 0.12
            },
            "keyboard_metrics": {
                "key_count": 14,
                "mean_dwell_ms": 86.0,
                "std_flight_ms": 32.5
            },
            "environment_signals": {
                "webdriver_flag": False,
                "plugins_count": 5,
                "languages_consistent": True,
                "viewport_ratio_valid": True,
                "time_to_first_interaction_ms": 420
            }
        }
        st, data, lat = self.ejecutar_test("IA", "POST", f"{IA_URL}/internal/predict", "/internal/predict (Humano)", 200, json_data=payload_humano)
        if st == 200 and isinstance(data, dict):
            print(f"      {GRAY}↳ Inferencia IA: score={data.get('risk_score')}, decisión={data.get('decision')}, latencia={data.get('latency_ms')} ms{RESET}")

        # 1.4 Inferencia de telemetría Bot (Debe clasificar bot)
        payload_bot = {
            "challenge_id": str(uuid.uuid4()),
            "telemetry_window_ms": 150,
            "pointer_metrics": {
                "event_count": 0,
                "mean_velocity": 0.0,
                "std_acceleration": 0.0,
                "angular_entropy": 0.0,
                "straight_line_ratio": 0.0
            },
            "keyboard_metrics": {
                "key_count": 0,
                "mean_dwell_ms": 0.0,
                "std_flight_ms": 0.0
            },
            "environment_signals": {
                "webdriver_flag": True,
                "plugins_count": 0,
                "languages_consistent": False,
                "viewport_ratio_valid": False,
                "time_to_first_interaction_ms": 0
            }
        }
        st_bot, data_bot, _ = self.ejecutar_test("IA", "POST", f"{IA_URL}/internal/predict", "/internal/predict (Bot)", 200, json_data=payload_bot)
        if st_bot == 200 and isinstance(data_bot, dict):
            print(f"      {GRAY}↳ Inferencia IA: score={data_bot.get('risk_score')}, decisión={data_bot.get('decision')}{RESET}")

    # =========================================================================
    # 2. BACKEND NÚCLEO SOBERANO (PUERTO 8000)
    # =========================================================================
    def probar_backend_nucleo(self) -> None:
        self.log_header("BACKEND NÚCLEO SOBERANO (APIs y Criptografía — Puerto 8000)")

        # 2.1 Health
        self.ejecutar_test("Backend", "GET", f"{BACKEND_URL}/health", "/health", 200)

        # 2.2 Políticas por defecto
        self.ejecutar_test("Backend", "GET", f"{BACKEND_URL}/api/v1/policies/default", "/api/v1/policies/default", 200)

        # 2.3 Challenge Init
        st, data_init, _ = self.ejecutar_test(
            "Backend", "POST", f"{BACKEND_URL}/api/v1/challenge/init",
            "/api/v1/challenge/init", 200,
            json_data={"site_key": "vh_site_9f8e7d6c5b4a3210", "target_route": "/login"}
        )

        cid = data_init.get("challenge_id") if isinstance(data_init, dict) else str(uuid.uuid4())
        nonce = data_init.get("nonce") or (data_init.get("pow") and data_init["pow"].get("nonce")) or "soberania"
        diff = data_init.get("pow_difficulty") or (data_init.get("pow") and data_init["pow"].get("difficulty")) or 2

        # 2.4 Challenge Verify (Resolviendo PoW y enviando telemetría humana)
        pow_sol = self.resolver_pow(nonce, diff)
        verify_payload = {
            "site_key": "vh_site_9f8e7d6c5b4a3210",
            "challenge_id": cid,
            "pow_solution": pow_sol,
            "telemetry": {
                "challenge_id": cid,
                "telemetry_window_ms": 2100,
                "pointer_metrics": {
                    "event_count": 42,
                    "mean_velocity": 1.30,
                    "std_acceleration": 0.40,
                    "angular_entropy": 2.78,
                    "straight_line_ratio": 0.14
                },
                "keyboard_metrics": {
                    "key_count": 10,
                    "mean_dwell_ms": 88.0,
                    "std_flight_ms": 30.0
                },
                "environment_signals": {
                    "webdriver_flag": False,
                    "plugins_count": 5,
                    "languages_consistent": True,
                    "viewport_ratio_valid": True,
                    "time_to_first_interaction_ms": 500
                }
            }
        }
        st_v, data_v, _ = self.ejecutar_test(
            "Backend", "POST", f"{BACKEND_URL}/api/v1/challenge/verify",
            "/api/v1/challenge/verify (Humano)", 200,
            json_data=verify_payload
        )
        if st_v == 200 and isinstance(data_v, dict) and data_v.get("jwt_token"):
            self.human_token = data_v["jwt_token"]
            print(f"      {GRAY}↳ Token Ed25519 obtenido: {self.human_token[:32]}...{RESET}")

        # 2.5 Login Administrativo con RBAC
        auth_payload = {
            "username": "admin_seguridad",
            "password": "Soberania2026!Segura"
        }
        st_a, data_a, _ = self.ejecutar_test(
            "Backend", "POST", f"{BACKEND_URL}/api/v1/admin/auth/login",
            "/api/v1/admin/auth/login", 200,
            json_data=auth_payload
        )
        if st_a == 200 and isinstance(data_a, dict) and data_a.get("access_token"):
            self.admin_token = data_a["access_token"]

        admin_headers = {"Authorization": f"Bearer {self.admin_token}"} if self.admin_token else {}

        # 2.6 Resumen de Observabilidad
        self.ejecutar_test("Backend", "GET", f"{BACKEND_URL}/api/v1/admin/observability/summary", "/api/v1/admin/observability/summary", 200, headers=admin_headers)

        # 2.7 Sitios Registrados
        self.ejecutar_test("Backend", "GET", f"{BACKEND_URL}/api/v1/admin/sites", "/api/v1/admin/sites", 200, headers=admin_headers)

        # 2.8 Bóveda de Claves Ed25519
        self.ejecutar_test("Backend", "GET", f"{BACKEND_URL}/api/v1/admin/vault/keys", "/api/v1/admin/vault/keys", 200, headers=admin_headers)

        # 2.9 Bitácora Inmutable de Auditoría (SHA-256)
        self.ejecutar_test("Backend", "GET", f"{BACKEND_URL}/api/v1/admin/audit-logs", "/api/v1/admin/audit-logs", 200, headers=admin_headers)

        # 2.10 Ingesta Interna de Eventos de Seguridad desde Borde
        ingest_payload = {
            "action": "rate_limited",
            "route": "/login",
            "reason": "prueba_diagnostico_script",
            "ip_hash": "sha256:d1a9n0571c0...",
            "risk_score": 0.85
        }
        self.ejecutar_test("Backend", "POST", f"{BACKEND_URL}/api/v1/internal/events/ingest", "/api/v1/internal/events/ingest", 200, json_data=ingest_payload)

    # =========================================================================
    # 3. CONSOLA ADMINISTRATIVA (PUERTO 3000)
    # =========================================================================
    def probar_consola_admin(self) -> None:
        self.log_header("CONSOLA ADMINISTRATIVA Y DE OBSERVABILIDAD (Puerto 3000)")

        # 3.1 Servidor estático
        self.ejecutar_test("Consola", "GET", f"{CONSOLA_URL}/", "/ (HTML Interfaz)", 200)
        self.ejecutar_test("Consola", "GET", f"{CONSOLA_URL}/app.js", "/app.js (Lógica Tiempo Real)", 200)
        self.ejecutar_test("Consola", "GET", f"{CONSOLA_URL}/styles.css", "/styles.css (Estilos)", 200)

        # 3.2 Proxy de observabilidad
        self.ejecutar_test("Consola", "GET", f"{CONSOLA_URL}/api/v1/admin/observability/summary", "/api/v1/admin/observability/summary (Proxy)", 200)

        # 3.3 Proxy de autenticación
        auth_payload = {
            "username": "admin_seguridad",
            "password": "Soberania2026!Segura"
        }
        self.ejecutar_test("Consola", "POST", f"{CONSOLA_URL}/api/v1/admin/auth/login", "/api/v1/admin/auth/login (Proxy)", 200, json_data=auth_payload)

    # =========================================================================
    # 4. BORDE PERIMETRAL TLS 1.3 Y DEMO INSTITUCIONAL (PUERTO 8443 / 8088)
    # =========================================================================
    def probar_borde_proxy(self) -> None:
        self.log_header("BORDE OPENRESTY TLS 1.3 Y APP PROTEGIDA (Puertos 8443 y 8088)")

        # 4.1 Redirección HTTP a HTTPS
        self.ejecutar_test("Borde", "GET", f"{BORDE_HTTP_URL}/health", "/health (HTTP -> Redirige 301)", 301, allow_redirects=False)

        # 4.2 Portal Ciudadano (Demo Web)
        self.ejecutar_test("Borde", "GET", f"{BORDE_URL}/", "/ (Portal Ciudadano HTML)", 200)
        self.ejecutar_test("Borde", "GET", f"{BORDE_URL}/health", "/health (Salud App Demo)", 200)

        # 4.3 Intentos no autorizados sin token (Deben ser bloqueados con 401 por OpenResty)
        self.ejecutar_test(
            "Borde", "POST", f"{BORDE_URL}/login",
            "/login (Sin Token -> Bloqueado 401)", 401,
            json_data={"cedula": "V-12345678", "password": "test"}
        )

        self.ejecutar_test(
            "Borde", "GET", f"{BORDE_URL}/api/consulta",
            "/api/consulta (Sin Token -> Bloqueado 401)", 401
        )

        # 4.4 Intentos con Token Inválido o Falsificado (Debe dar 401)
        headers_falso = {"X-Human-Token": "token_falso_invalido.firmado_con_clave_desconocida"}
        self.ejecutar_test(
            "Borde", "POST", f"{BORDE_URL}/login",
            "/login (Token Falso -> Bloqueado 401)", 401,
            headers=headers_falso,
            json_data={"cedula": "V-12345678", "password": "test"}
        )

        # 4.5 Desafío y Verificación a través del Borde TLS 1.3
        st_b_init, d_b_init, _ = self.ejecutar_test(
            "Borde", "POST", f"{BORDE_URL}/api/v1/challenge/init",
            "/api/v1/challenge/init (Vía Borde)", 200,
            json_data={"site_key": "vh_site_9f8e7d6c5b4a3210", "target_route": "/login"}
        )

        b_cid = d_b_init.get("challenge_id") if isinstance(d_b_init, dict) else str(uuid.uuid4())
        b_nonce = d_b_init.get("nonce") or (d_b_init.get("pow") and d_b_init["pow"].get("nonce")) or "borde_nonce"
        b_diff = d_b_init.get("pow_difficulty") or (d_b_init.get("pow") and d_b_init["pow"].get("difficulty")) or 2
        b_sol = self.resolver_pow(b_nonce, b_diff)

        b_verify_payload = {
            "site_key": "vh_site_9f8e7d6c5b4a3210",
            "challenge_id": b_cid,
            "pow_solution": b_sol,
            "telemetry": {
                "challenge_id": b_cid,
                "telemetry_window_ms": 2200,
                "pointer_metrics": {
                    "event_count": 45,
                    "mean_velocity": 1.28,
                    "std_acceleration": 0.42,
                    "angular_entropy": 2.80,
                    "straight_line_ratio": 0.13
                },
                "keyboard_metrics": {
                    "key_count": 12,
                    "mean_dwell_ms": 85.0,
                    "std_flight_ms": 31.0
                },
                "environment_signals": {
                    "webdriver_flag": False,
                    "plugins_count": 5,
                    "languages_consistent": True,
                    "viewport_ratio_valid": True,
                    "time_to_first_interaction_ms": 480
                }
            }
        }
        st_b_ver, d_b_ver, _ = self.ejecutar_test(
            "Borde", "POST", f"{BORDE_URL}/api/v1/challenge/verify",
            "/api/v1/challenge/verify (Vía Borde)", 200,
            json_data=b_verify_payload
        )

        token_borde = d_b_ver.get("jwt_token") if (st_b_ver == 200 and isinstance(d_b_ver, dict)) else self.human_token

        # 4.6 Acceso Exitoso con Token Válido a Rutas Protegidas en Borde
        if token_borde:
            headers_validos = {"X-Human-Token": token_borde}
            self.ejecutar_test(
                "Borde", "POST", f"{BORDE_URL}/login",
                "/login (Con Token Válido -> 200 Autorizado)", 200,
                headers=headers_validos,
                json_data={"cedula": "V-12345678", "password": "clave_ciudadana"}
            )

            self.ejecutar_test(
                "Borde", "GET", f"{BORDE_URL}/api/consulta",
                "/api/consulta (Con Token Válido -> 200 OK)", 200,
                headers=headers_validos
            )
        else:
            print(f"      {YELLOW}⚠ No se obtuvo token válido para probar rutas autorizadas.{RESET}")

    def imprimir_resumen(self) -> None:
        total = len(self.results)
        pasados = sum(1 for r in self.results if r["exito"])
        fallidos = total - pasados
        pct = (pasados / total * 100.0) if total > 0 else 0.0

        self.log_header("RESUMEN DE AUDITORÍA Y COBERTURA DE ENDPOINTS")
        print(f"  • Total Endpoints / Escenarios evaluados: {BOLD}{total}{RESET}")
        print(f"  • Exitosos ({GREEN}PASÓ{RESET}): {BOLD}{GREEN}{pasados}{RESET}")
        print(f"  • Fallidos ({RED}FALLÓ{RESET}): {BOLD}{RED if fallidos > 0 else GREEN}{fallidos}{RESET}")
        print(f"  • Tasa de Cumplimiento: {BOLD}{GREEN if pct == 100 else YELLOW}{pct:.1f} %{RESET}\n")

        # Agrupado por Módulo
        modulos = sorted(list(set(r["modulo"] for r in self.results)))
        for m in modulos:
            m_tests = [r for r in self.results if r["modulo"] == m]
            m_pas = sum(1 for r in m_tests if r["exito"])
            m_tot = len(m_tests)
            prom_lat = sum(r["latencia_ms"] for r in m_tests) / m_tot if m_tot > 0 else 0.0
            print(f"  [{m:<10}] {m_pas}/{m_tot} tests exitosos | Latencia media: {prom_lat:5.1f} ms")
        print()


def main() -> None:
    tester = EndpointTester()
    tester.probar_ia_conductual()
    tester.probar_backend_nucleo()
    tester.probar_consola_admin()
    tester.probar_borde_proxy()
    tester.imprimir_resumen()

if __name__ == "__main__":
    main()
