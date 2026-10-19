import { RoutesAlias } from '../../router/routesAlias'

/** 登录后无有效 redirect 时进入后台首页 */
export const DEFAULT_HOME_PATH = '/dashboard/console'

const AUTH_PATHS = [RoutesAlias.Login, '/auth/register', '/auth/forget-password', '/login']
const ERROR_PATHS = ['/403', '/404', '/500']

function firstQuery(raw: unknown): string {
  if (Array.isArray(raw)) return String(raw[0] ?? '')
  return typeof raw === 'string' ? raw : ''
}

function decodeOnce(value: string): string {
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

function pathOnly(url: string): string {
  return url.split('?')[0].split('#')[0] || ''
}

function isAuthPath(path: string): boolean {
  return AUTH_PATHS.some((p) => path === p || path.startsWith(`${p}/`))
}

function isErrorPath(path: string): boolean {
  return ERROR_PATHS.includes(path) || path.startsWith('/exception/')
}

/**
 * 展开 login?redirect=login?redirect=/x 这类嵌套参数，得到真正要去的相对路径。
 */
export function unwrapLoginRedirect(raw: unknown, depth = 0): string {
  if (depth > 6) return ''
  let value = decodeOnce(firstQuery(raw)).trim()
  if (!value) return ''

  const hashIdx = value.indexOf('#/')
  if (hashIdx >= 0) {
    value = value.slice(hashIdx + 1)
  }

  if (/^[a-z]+:/i.test(value) || value.startsWith('//')) return ''

  if (!value.startsWith('/')) {
    value = `/${value}`
  }

  const qIndex = value.indexOf('?')
  const path = pathOnly(qIndex >= 0 ? value.slice(0, qIndex) : value)
  const query = qIndex >= 0 ? value.slice(qIndex + 1) : ''

  if (isAuthPath(path)) {
    const marker = 'redirect='
    const i = query.indexOf(marker)
    if (i < 0) return ''
    return unwrapLoginRedirect(query.slice(i + marker.length), depth + 1)
  }

  return qIndex >= 0 ? `${path}?${query}` : path
}

/** 登出时是否把当前页当作 redirect：排除登录页和错误页 */
export function isLoginRedirectTarget(fullPath: string): boolean {
  const path = pathOnly(unwrapLoginRedirect(fullPath) || fullPath)
  return Boolean(path) && !isAuthPath(path) && !isErrorPath(path)
}

/**
 * 登录成功 / 已登录访问登录页时的最终跳转。
 * 错误页（403/404/500）视为无效目标，回到后台首页。
 */
export function resolveLoginRedirect(raw: unknown, fallback = DEFAULT_HOME_PATH): string {
  const target = unwrapLoginRedirect(raw)
  if (!target) return fallback
  const path = pathOnly(target)
  if (isAuthPath(path) || isErrorPath(path)) return fallback
  return target
}

/** ponytail: unwrap + 错误页回首页；失败即抛 */
export function checkLoginRedirect(): void {
  const eq = (got: string, want: string) => {
    if (got !== want) throw new Error(`loginRedirect: ${JSON.stringify(got)} !== ${JSON.stringify(want)}`)
  }
  eq(unwrapLoginRedirect('/auth/login?redirect=/safeguard/login-log'), '/safeguard/login-log')
  eq(
    unwrapLoginRedirect('/auth/login?redirect=/auth/login?redirect=/safeguard/login-log'),
    '/safeguard/login-log'
  )
  eq(unwrapLoginRedirect('/auth/login?redirect=/auth/login?redirect=/500'), '/500')
  eq(resolveLoginRedirect('/auth/login?redirect=/safeguard/login-log'), '/safeguard/login-log')
  eq(resolveLoginRedirect('/auth/login?redirect=/auth/login?redirect=/500'), DEFAULT_HOME_PATH)
  eq(resolveLoginRedirect('/500'), DEFAULT_HOME_PATH)
  eq(resolveLoginRedirect(undefined), DEFAULT_HOME_PATH)
  eq(resolveLoginRedirect('https://evil.example/phish'), DEFAULT_HOME_PATH)
  if (isLoginRedirectTarget('/safeguard/login-log') !== true) throw new Error('target login-log')
  if (isLoginRedirectTarget('/500') !== false) throw new Error('target 500')
  if (isLoginRedirectTarget('/auth/login') !== false) throw new Error('target login')
}
