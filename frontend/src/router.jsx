import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

const RouterContext = createContext(null)

export function RouterProvider({ children }) {
  const [pathname, setPathname] = useState(() => window.location.pathname || '/')

  useEffect(() => {
    const handlePopState = () => setPathname(window.location.pathname || '/')
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  const navigate = useCallback((to, options = {}) => {
    const target = typeof to === 'string' && to.startsWith('/') ? to : '/'
    if (options.replace) window.history.replaceState({}, '', target)
    else window.history.pushState({}, '', target)
    setPathname(target)
    window.scrollTo({ top: 0, left: 0 })
  }, [])

  const value = useMemo(() => ({ pathname, navigate }), [pathname, navigate])
  return <RouterContext.Provider value={value}>{children}</RouterContext.Provider>
}

function useRouter() {
  const router = useContext(RouterContext)
  if (!router) throw new Error('RouterProvider is missing')
  return router
}

export function usePathname() {
  return useRouter().pathname
}

export function useNavigate() {
  return useRouter().navigate
}

export function Redirect({ to, replace = true }) {
  const navigate = useNavigate()
  useEffect(() => { navigate(to, { replace }) }, [navigate, replace, to])
  return null
}

export function Link({ to, onClick, target, children, ...props }) {
  const navigate = useNavigate()

  function handleClick(event) {
    onClick?.(event)
    if (
      event.defaultPrevented ||
      event.button !== 0 ||
      event.metaKey || event.ctrlKey || event.shiftKey || event.altKey ||
      target === '_blank'
    ) return
    event.preventDefault()
    navigate(to)
  }

  return <a href={to} target={target} onClick={handleClick} {...props}>{children}</a>
}
