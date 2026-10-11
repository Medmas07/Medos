import { useEffect, useState } from 'react'
import { JourneyApp } from './JourneyApp'
import { Landing } from './landing/Landing'
import { routeFromHash } from './route'
import { SignInPage } from './SignInPage'

/** MedOS web entry: landing page, sign-in page, and guided onboarding journey (see route.ts). */
export default function App() {
  const [route, setRoute] = useState(() => routeFromHash(window.location.hash))

  useEffect(() => {
    const handleHashChange = () => setRoute(routeFromHash(window.location.hash))
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  if (route.kind === 'journey') return <JourneyApp step={route.step} />
  if (route.kind === 'signin') return <SignInPage />
  return <Landing />
}
