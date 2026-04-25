/**
 * Wrapper around pywebview.api for type-safe calls.
 */
function getApi() {
  if (typeof pywebview !== 'undefined' && pywebview.api) {
    return pywebview.api
  }
  return null
}

export async function apiCall(method, ...args) {
  const api = getApi()
  if (!api) {
    console.warn(`[useApi] pywebview.api not available, skipping ${method}`)
    return null
  }
  try {
    return await api[method](...args)
  } catch (e) {
    console.error(`[useApi] ${method} failed:`, e)
    throw e
  }
}
