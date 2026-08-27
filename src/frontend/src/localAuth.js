// localAuth.js — Autenticación del frontend embebido contra el backend
// FastAPI local (ver hallazgo C1 de la auditoría de seguridad).
//
// El backend local expone TODOS los endpoints /api/* protegidos por un
// token secreto aleatorio generado al arrancar la app (header
// "X-Local-Auth-Token"), salvo /api/bootstrap/token que lo entrega una
// única vez. Este módulo:
//   1. Obtiene el token desde /api/bootstrap/token al cargar la app.
//   2. Parchea window.fetch para inyectar automáticamente el header en
//      cualquier llamada a una ruta relativa /api/* (el backend local),
//      sin tener que tocar cada uno de los call-sites existentes en
//      App.jsx. Las llamadas a URLs absolutas (servidor remoto, distinto
//      origen) no se ven afectadas.

let _localAuthToken = null
let _bootstrapPromise = null

function isLocalApiRequest(input) {
  try {
    const url = typeof input === 'string' ? input : (input && input.url) || ''
    // Solo interceptar rutas relativas al propio backend local (mismo origen),
    // nunca URLs absolutas (esas van al servidor remoto configurado por el usuario).
    return url.startsWith('/api/') && !url.startsWith('/api/bootstrap/')
  } catch {
    return false
  }
}

export async function initLocalAuth() {
  if (_bootstrapPromise) return _bootstrapPromise
  _bootstrapPromise = (async () => {
    try {
      const res = await window.__nativeFetch('/api/bootstrap/token')
      const data = await res.json()
      _localAuthToken = data.token || null
    } catch (e) {
      console.error('No se pudo obtener el token de autenticación local:', e)
    }
    return _localAuthToken
  })()
  return _bootstrapPromise
}

// Expone el token para casos que no pasan por window.fetch (p. ej. el
// WebSocket de logs en tiempo real, que no puede llevar headers custom en
// el handshake y necesita adjuntar el token como query param).
export async function getLocalAuthToken() {
  if (_localAuthToken === null) {
    await initLocalAuth()
  }
  return _localAuthToken
}

export function installLocalAuthFetchInterceptor() {
  if (window.__nativeFetch) return // ya instalado
  window.__nativeFetch = window.fetch.bind(window)

  window.fetch = async (input, init = {}) => {
    if (!isLocalApiRequest(input)) {
      return window.__nativeFetch(input, init)
    }

    if (_localAuthToken === null) {
      await initLocalAuth()
    }

    const headers = new Headers(init.headers || (typeof input !== 'string' ? input.headers : undefined))
    if (_localAuthToken) {
      headers.set('X-Local-Auth-Token', _localAuthToken)
    }

    return window.__nativeFetch(input, { ...init, headers })
  }
}
