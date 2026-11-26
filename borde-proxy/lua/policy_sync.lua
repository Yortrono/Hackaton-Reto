-- ==============================================================================
-- policy_sync.lua — Sincronización Dinámica de Políticas de Borde
-- Servicio Autónomo de Verificación Humana y Mitigación de Bots
-- Hackathon Venezuela Innova 2026 - Dev 2 (IA, Borde e Infraestructura)
-- ==============================================================================

local http = require("resty.http")
local cjson = require("cjson.safe")

local policies_cache = ngx.shared.policies_cache
local BACKEND_URL = "http://backend-nucleo:8000/api/v1/policies/default"
local FALLBACK_FILE = "/usr/local/openresty/nginx/default_policy.json"

local function load_fallback_policy()
    local file, err = io.open(FALLBACK_FILE, "r")
    if not file then
        ngx.log(ngx.ERR, "[borde-proxy] Error al abrir politica fallback: ", err)
        return nil
    end

    local content = file:read("*a")
    file:close()

    local data, json_err = cjson.decode(content)
    if not data then
        ngx.log(ngx.ERR, "[borde-proxy] Error parseando JSON de politica fallback: ", json_err)
        return nil
    end

    policies_cache:set("policy_data", content)
    policies_cache:set("policy_source", "local_fallback")
    policies_cache:set("last_sync", ngx.time())
    ngx.log(ngx.INFO, "[borde-proxy] Politica fallback cargada exitosamente desde disco.")
    return data
end

local function sync_policy(premature)
    if premature then
        return
    end

    local httpc = http.new()
    httpc:set_timeouts(1000, 2000, 2000) -- 1s conexion, 2s lectura

    local res, err = httpc:request_uri(BACKEND_URL, {
        method = "GET",
        headers = {
            ["Accept"] = "application/json",
            ["User-Agent"] = "BordeProxy-PolicySync/1.0"
        }
    })

    if res and res.status == 200 then
        local data, json_err = cjson.decode(res.body)
        if data then
            policies_cache:set("policy_data", res.body)
            policies_cache:set("policy_source", "backend_dynamic")
            policies_cache:set("last_sync", ngx.time())
            ngx.log(ngx.INFO, "[borde-proxy] Politicas sincronizadas dinamicamente desde Backend Núcleo.")
            return
        else
            ngx.log(ngx.WARN, "[borde-proxy] Respuesta backend invalida: ", json_err)
        end
    else
        -- Backend no responde aún o falló; mantener caché o cargar fallback
        local cached = policies_cache:get("policy_data")
        if not cached then
            load_fallback_policy()
        end
    end
end

-- Ejecución inicial al arrancar el worker
local ok, err = ngx.timer.at(0, sync_policy)
if not ok then
    ngx.log(ngx.ERR, "[borde-proxy] Error al programar sync inicial: ", err)
    load_fallback_policy()
end

-- Ciclo periódico cada 5 segundos
local ok_every, err_every = ngx.timer.every(5, sync_policy)
if not ok_every then
    ngx.log(ngx.ERR, "[borde-proxy] Error al programar sync recurrente: ", err_every)
end
