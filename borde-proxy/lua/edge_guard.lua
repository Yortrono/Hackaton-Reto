-- ==============================================================================
-- edge_guard.lua — Capa de Borde Inteligente (DDoS L7, Rate Limiting y JWT)
-- Servicio Autónomo de Verificación Humana y Mitigación de Bots
-- Hackathon Venezuela Innova 2026 - Dev 2 (IA, Borde e Infraestructura)
-- ==============================================================================

local cjson = require("cjson.safe")
local jwt = require("resty.jwt")
local str = require("resty.string")
local http = require("resty.http")

local policies_cache = ngx.shared.policies_cache
local rate_limit_store = ngx.shared.rate_limit_store

local function generate_trace_id()
    local template = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx"
    return string.gsub(template, "[xy]", function (c)
        local v = (c == "x") and math.random(0, 0xf) or math.random(8, 0xb)
        return string.format("%x", v)
    end)
end

local function get_iso_timestamp()
    return os.date("!%Y-%m-%dT%H:%M:%SZ", ngx.time())
end

-- Envío asíncrono no bloqueante de evento de seguridad a backend-nucleo con deduplicación
local function report_security_event_async(action, route, reason, ip_hash, risk_score)
    -- Deduplicación perimetral: evitar saturar el backend con ráfagas masivas de la misma IP
    if ip_hash then
        local rpt_key = "rpt:" .. ip_hash .. ":" .. action
        local already = rate_limit_store:get(rpt_key)
        if already then
            return
        end
        rate_limit_store:set(rpt_key, true, 1) -- 1 segundo de deduplicación
    end

    ngx.timer.at(0, function(premature)
        if premature then return end
        local httpc = http.new()
        httpc:set_timeouts(400, 400, 400)
        local payload = cjson.encode({
            action = action,
            route = route,
            reason = reason,
            ip_hash = ip_hash,
            risk_score = risk_score or 0.99
        })
        local res, err = httpc:request_uri("http://backend-nucleo:8000/api/v1/internal/events/ingest", {
            method = "POST",
            headers = { ["Content-Type"] = "application/json" },
            body = payload
        })
        if res and res.status == 200 then
            httpc:set_keepalive(10000, 50)
        end
    end)
end

local function send_error(status_code, err_code, message, details)
    local trace_id = generate_trace_id()
    local payload = {
        error = {
            code = err_code,
            message = message,
            trace_id = trace_id,
            timestamp = get_iso_timestamp(),
            details = details or {}
        }
    }
    ngx.status = status_code
    ngx.header["Content-Type"] = "application/json; charset=utf-8"
    ngx.header["X-Trace-ID"] = trace_id
    ngx.say(cjson.encode(payload))
    return ngx.exit(status_code)
end

-- ------------------------------------------------------------------------------
-- 1. Cargar Política Activa desde Caché o Archivo Local
-- ------------------------------------------------------------------------------
local policy_raw = policies_cache:get("policy_data")
local policy = nil

if policy_raw then
    policy = cjson.decode(policy_raw)
end

if not policy or not policy.policy then
    policy = {
        mode = "challenge",
        ai_thresholds = { challenge_min = 0.35, block_min = 0.75 },
        rate_limit_global_rpm = 120,
        protected_routes = {
            { path_prefix = "/login", methods = {"POST"}, require_token = true, rate_limit_rpm = 10 },
            { path_prefix = "/api/consulta", methods = {"GET", "POST"}, require_token = true, rate_limit_rpm = 30 }
        },
        ip_whitelist = {"127.0.0.1", "10.0.0.0/8"},
        ip_blacklist = {"198.51.100.42"}
    }
else
    policy = policy.policy
end

-- ------------------------------------------------------------------------------
-- 2. Inspección Perimetral y Mitigación de Bots Básicos (Cabeceras y Límites L7)
-- ------------------------------------------------------------------------------
local client_ip = ngx.var.http_x_forwarded_for or ngx.var.remote_addr or "127.0.0.1"
if string.find(client_ip, ",") then
    client_ip = string.match(client_ip, "^([^,]+)")
end

local user_agent = ngx.var.http_user_agent
if not user_agent or user_agent == "" then
    report_security_event_async("blocked", ngx.var.uri, "missing_user_agent", "sha256:unknown", 0.99)
    return send_error(403, "BOT_BLOCKED", "Petición rechazada: Cabecera User-Agent obligatoria en el borde perimetral.", {
        client_ip = "anonimizada",
        violation = "empty_user_agent"
    })
end

local content_length = tonumber(ngx.var.http_content_length) or 0
if content_length > 1048576 then
    return send_error(413, "PAYLOAD_TOO_LARGE", "El tamaño de la petición supera el límite permitido de 1 MB.", {
        max_bytes = 1048576,
        received_bytes = content_length
    })
end

-- ------------------------------------------------------------------------------
-- 3. Verificación de Listas Negras y Blancas de IP (CIDR / Exacta)
-- ------------------------------------------------------------------------------
if policy.ip_blacklist then
    for _, blocked_ip in ipairs(policy.ip_blacklist) do
        if client_ip == blocked_ip then
            return send_error(403, "IP_BLOCKED", "Dirección IP bloqueada por política de seguridad soberana.", {
                action = "drop_connection"
            })
        end
    end
end

-- ------------------------------------------------------------------------------
-- 4. Rate Limiting Multicapa con Anonimización Efímera de IP
-- ------------------------------------------------------------------------------
local salt = "soberania_local_2026_salt"
local ip_hash_val = "sha256:" .. str.to_hex(ngx.sha1_bin(client_ip .. salt)):sub(1, 12) .. "..."

local uri = ngx.var.uri
local method = ngx.req.get_method()

local limit_rpm = policy.rate_limit_global_rpm or 120
local matched_route = nil

if policy.protected_routes then
    for _, r in ipairs(policy.protected_routes) do
        if string.sub(uri, 1, string.len(r.path_prefix)) == r.path_prefix then
            matched_route = r
            if r.rate_limit_rpm then
                limit_rpm = r.rate_limit_rpm
            end
            break
        end
    end
end

local current_slot = math.floor(ngx.time() / 60)
local route_tag = matched_route and matched_route.path_prefix or "global"
local rl_key = ip_hash_val .. ":" .. route_tag .. ":" .. current_slot

local count, err = rate_limit_store:incr(rl_key, 1, 0, 65)

if count and count > limit_rpm then
    ngx.header["Retry-After"] = "60"
    report_security_event_async("rate_limited", uri, "rpm_threshold_exceeded", ip_hash_val, 0.85)
    return send_error(429, "RATE_LIMIT_EXCEEDED", "Límite de peticiones por minuto excedido en el borde perimetral.", {
        limit_rpm = limit_rpm,
        current_requests = count,
        retry_after_seconds = 60,
        route = route_tag
    })
end

-- ------------------------------------------------------------------------------
-- 5. Verificación de Rutas Protegidas y Validación de Token JWT
-- ------------------------------------------------------------------------------
local require_token = false
if matched_route and matched_route.require_token then
    if matched_route.methods then
        for _, m in ipairs(matched_route.methods) do
            if m == method then
                require_token = true
                break
            end
        end
    else
        require_token = true
    end
end

local policy_mode = policy.mode or "challenge"

if require_token and policy_mode ~= "monitor" then
    local headers = ngx.req.get_headers()
    local token = headers["x-human-token"] or ngx.var.cookie_vh_token

    if not token or token == "" then
        report_security_event_async("blocked", uri, "token_required_missing", ip_hash_val, 0.95)
        return send_error(401, "VERIFICATION_REQUIRED", "Se requiere token de verificación humana válido para acceder a esta ruta.", {
            policy_mode = policy_mode,
            protected_route = uri,
            method = method
        })
    end

    local jwt_obj = jwt:load_jwt(token)
    if not jwt_obj.valid then
        report_security_event_async("blocked", uri, "invalid_jwt_signature", ip_hash_val, 0.98)
        return send_error(401, "INVALID_TOKEN", "Estructura de token JWT inválida o malformada.", {
            reason = jwt_obj.reason or "invalid_jwt_structure"
        })
    end

    local exp = jwt_obj.payload and jwt_obj.payload.exp
    if exp and tonumber(exp) < ngx.time() then
        report_security_event_async("blocked", uri, "expired_token", ip_hash_val, 0.90)
        return send_error(401, "INVALID_TOKEN", "El token de verificación humana ha expirado.", {
            expired_at = exp,
            current_time = ngx.time()
        })
    end

    ngx.req.set_header("X-Verified-Human", "true")
    if jwt_obj.payload and jwt_obj.payload.risk_score then
        ngx.req.set_header("X-Human-Risk-Score", tostring(jwt_obj.payload.risk_score))
    end
end
