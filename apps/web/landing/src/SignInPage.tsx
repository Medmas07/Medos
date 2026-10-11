import type { FormEvent } from 'react'
import { Alert, Button, Card, TextField, ThemeToggle } from '@hackcure/design-system'
import { Logo } from './landing/Logo'

/**
 * Simple sign-in page. Authentication is not implemented: submitting does
 * nothing yet; nothing is checked, stored, sent, or opened.
 */
export function SignInPage() {
  // No destination until authentication exists.
  const submit = (event: FormEvent<HTMLFormElement>) => event.preventDefault()

  return (
    <div className="flex min-h-dvh flex-col bg-paper">
      <header className="mx-auto flex h-16 w-full max-w-[1320px] items-center justify-between gap-4 px-4 sm:px-8">
        <a href={import.meta.env.BASE_URL} aria-label="Accueil MedOS" className="rounded-lg">
          <Logo />
        </a>
        <ThemeToggle />
      </header>
      <main className="flex flex-1 items-center justify-center px-4 py-10">
        <div className="w-full max-w-md animate-page space-y-4">
          <div className="text-center">
            <h1>Se connecter</h1>
            <p className="mt-2 text-ink-soft">Accédez au dossier d'adhésion de votre établissement.</p>
          </div>
          <Card>
            <form onSubmit={submit} className="space-y-4">
              <TextField label="E-mail professionnel" type="email" autoComplete="email" required />
              <TextField label="Mot de passe" type="password" autoComplete="current-password" required />
              <Button type="submit" className="w-full">
                Se connecter
              </Button>
            </form>
          </Card>
          <Alert tone="info" title="Connexion simulée">
            L'authentification n'est pas encore implémentée : rien n'est vérifié ni envoyé.
          </Alert>
        </div>
      </main>
    </div>
  )
}
