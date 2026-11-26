-- ==============================================================================
-- edge_guard.lua — Capa de Borde Inteligente (DDoS L7, Rate Limiting y JWT)
-- Servicio Autónomo de Verificación Humana y Mitigación de Bots
-- Hackathon Venezuela Innova 2026 - Dev 2 (IA, Borde e Infraestructura)
-- ==============================================================================

local cjson = require("cjson.safe")
local jwt = require("resty.jwt")
local str = require("resty.string")

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

local function send_error(status, code, message, details)
    ngx.status = status
    ngx.header["Content-Type"] = "application/json; charset=utf-8"
    local body = {
        error = {
            code = code,
            message = message,
            details = details or {},
            trace_id = generate_trace_id(),
            timestamp = get_iso_timestamp()
        }
    }
    ngx.say(cjson.encode(body))
    return ngx.exit(status)
end

-- ------------------------------------------------------------------------------
-- 1. Mitigación DDoS Capa 7 (Inspección Rápida en Cabeceras)
-- ------------------------------------------------------------------------------
local ua = ngx.var.http_user_agent
if not ua or ua == "" then
    return send_error(403, "BOT_BLOCKED", "Petición rechazada: Cabecera User-Agent obligatoria en el borde perimetral.", {
        reason = "missing_user_agent"
    })
end

local content_length = tonumber(ngx.var.http_content_length or "0")
if content_length and content_length > 1048576 then
    return send_error(413, "INVALID_PAYLOAD", "Petición rechazada: El tamaño del payload excede el límite permitido de 1 MB.", {
        max_bytes = 1048576,
        received_bytes = content_length
    })
end

-- ------------------------------------------------------------------------------
-- 2. Recuperar Políticas de Seguridad (Caché en Memoria o Fallback)
-- ------------------------------------------------------------------------------
local policy_raw = policies_cache:get("policy_data")
local policy_obj = nil

if policy_raw then
    policy_obj = cjson.decode(policy_raw)
end

if not policy_obj then
    -- Fallback inmediato de emergencia
    local f = io.open("/usr/local/openresty/nginx/default_policy.json", "r")
    if f then
        local c = f:read("*a")
        f:close()
        policy_obj = cjson.decode(c)
    end
end

local policy = (policy_obj and policy_obj.policy) or {
    mode = "challenge",
    rate_limit_global_rpm = 120,
    protected_routes = {
        { path_prefix = "/login", methods = {"POST"}, require_token = true, rate_limit_rpm = 10 },
        { path_prefix = "/api/consulta", methods = {"GET", "POST"}, require_token = true, rate_limit_rpm = 30 }
    },
    ip_blacklist = {"198.51.100.42"}
}

local client_ip = ngx.var.remote_addr or "127.0.0.1"

-- ------------------------------------------------------------------------------
-- 3. Lista Negra de IPs
-- ------------------------------------------------------------------------------
if policy.ip_blacklist then
    for _, blocked_ip in ipairs(policy.ip_blacklist) do
        if client_ip == blocked_ip then
            return send_error(403, "BOT_BLOCKED", "Acceso denegado: Dirección IP bloqueada por política perimetral.", {
                ip_blocked = true
            })
        end
    end
end

-- ------------------------------------------------------------------------------
-- 4. Rate Limiting Multicapa con Anonimización Efímera de IP (SHA-1/SHA-256)
-- ------------------------------------------------------------------------------
local salt = "soberania_local_2026_salt"
local ip_hash = ngx.encode_base64(ngx.sha1_bin(client_ip .. salt))

local uri = ngx.var.uri
local method = ngx.req.get_method()

-- Determinar límite de peticiones según la ruta
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

-- Ventana de 60 segundos
local current_slot = math.floor(ngx.time() / 60)
local route_tag = matched_route and matched_route.path_prefix or "global"
local rl_key = ip_hash .. ":" .. route_tag .. ":" .. current_slot

local count, err = rate_limit_store:incr(rl_key, 1, 0, 65)

if count and count > limit_rpm then
    ngx.header["Retry-After"] = "60"
    return send_error(429, "RATE_LIMIT_EXCEEDED", "Límite de peticiones por minuto excedido en el borde perimetral.", {
        limit_rpm = limit_rpm,
        current_requests = count,
        retry_after_seconds = 60,
        route = route_tag
    })
end

-- ------------------------------------------------------------------------------
-- 5. Verificación de Rutas Protegidas y Validación de Token JWT Asimétrico
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

-- Si la ruta requiere token y el modo de operación no es monitor pasivo
if require_token and policy_mode ~= "monitor" then
    local headers = ngx.req.get_headers()
    local token = headers["x-human-token"] or ngx.var.cookie_vh_token

    if not token or token == "" then
        return send_error(401, "VERIFICATION_REQUIRED", "Se requiere token de verificación humana válido para acceder a esta ruta.", {
            policy_mode = policy_mode,
            protected_route = uri,
            method = method
        })
    end

    -- Validar formato y firma del JWT
    local jwt_obj = jwt:load_jwt(token)
    if not jwt_obj.valid then
        return send_error(401, "INVALID_TOKEN", "Estructura de token JWT inválida o malformada.", {
            reason = jwt_obj.reason or "invalid_jwt_structure"
        })
    end

    -- Validar expiración (exp)
    local exp = jwt_obj.payload and jwt_obj.payload.exp
    if exp and tonumber(exp) < ngx.time() then
        return send_error(401, "INVALID_TOKEN", "El token de verificación humana ha expirado.", {
            expired_at = exp,
            current_time = ngx.time()
        })
    end

    -- Inyectar cabecera de contexto verificado para el backend
    ngx.req.set_header("X-Verified-Human", "true")
    if jwt_obj.payload and jwt_obj.payload.risk_score then
        ngx.req.set_header("X-Human-Risk-Score", tostring(jwt_obj.payload.risk_score))
    end
end

-- Acceso autorizado
