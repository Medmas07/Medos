import { useState } from 'react'
import { Badge, Button, DemoBanner, SelectField, TextField } from '@hackcure/design-system'
import {
  authService,
  CANONICAL_DEMO_IDENTITIES,
  type DemoAuthScenario,
  type DemoIdentity,
} from '../../services/authService'

interface DemoAuthModalProps {
  isOpen: boolean
  onClose: () => void
}

export function DemoAuthModal({ isOpen, onClose }: DemoAuthModalProps) {
  const currentSession = authService.getCurrentSession()
  const [selectedIdentityId, setSelectedIdentityId] = useState<string>(
    currentSession?.identity.id ?? 'usr-olfa',
  )
  const [scenario, setScenario] = useState<DemoAuthScenario>('nominal')
  const [password, setPassword] = useState<string>('demo')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(false)

  if (!isOpen) return null

  const selectedIdentity: DemoIdentity =
    CANONICAL_DEMO_IDENTITIES.find((i) => i.id === selectedIdentityId) ?? CANONICAL_DEMO_IDENTITIES[0]

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setErrorMessage(null)

    setTimeout(() => {
      setIsLoading(false)
      const res = authService.login(selectedIdentityId, {
        scenario,
        password,
      })

      if (res.kind === 'error') {
        setErrorMessage(res.message)
      } else {
        onClose()
      }
    }, 250)
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-xs"
      role="dialog"
      aria-modal="true"
      aria-labelledby="demo-auth-title"
    >
      <div className="relative w-full max-w-2xl rounded-2xl bg-white p-6 shadow-2xl ring-1 ring-slate-900/10">
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h2 id="demo-auth-title" className="text-xl font-bold text-slate-900">
              Flux d'authentification démo (HC-210)
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Sélectionnez une identité canonique (HC-005) et un scénario pour tester le contrôle d'accès.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            aria-label="Fermer"
          >
            ✕
          </button>
        </div>

        <div className="mb-4">
          <DemoBanner>
            Démonstration D1 : identités déterministes et sessions simulées. Aucune vérification cryptographique
            ni mot de passe de production.
          </DemoBanner>
        </div>

        {errorMessage && (
          <div className="mb-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-700 ring-1 ring-rose-200">
            {errorMessage}
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-700">
              1. Choisir une identité démo
            </label>
            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
              {CANONICAL_DEMO_IDENTITIES.map((identity) => {
                const isSelected = identity.id === selectedIdentityId
                return (
                  <button
                    key={identity.id}
                    type="button"
                    onClick={() => setSelectedIdentityId(identity.id)}
                    className={`flex flex-col items-start rounded-xl p-3 text-left transition-all ${
                      isSelected
                        ? 'bg-brand-50/80 ring-2 ring-brand-600'
                        : 'bg-slate-50 hover:bg-slate-100 ring-1 ring-slate-200'
                    }`}
                  >
                    <div className="flex w-full items-center justify-between">
                      <span className="font-semibold text-slate-900">{identity.displayName}</span>
                      <Badge
                        tone={identity.role === 'governance_reviewer' ? 'success' : 'neutral'}
                        dot={identity.role === 'governance_reviewer'}
                      >
                        {identity.role}
                      </Badge>
                    </div>
                    <span className="mt-1 text-xs text-slate-600">{identity.organizationName}</span>
                    <span className="mt-1 text-[11px] text-slate-500 line-clamp-1">{identity.description}</span>
                  </button>
                )
              })}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <SelectField
              id="demo-scenario-select"
              label="2. Scénario simulé"
              value={scenario}
              onChange={(e) => setScenario(e.target.value as DemoAuthScenario)}
              options={[
                { value: 'nominal', label: 'Nominal (Session active 200)' },
                { value: 'expired', label: 'Expirée (Simulation 401)' },
                { value: 'invalid_credentials', label: 'Échec identifiants (Erreur 401)' },
              ]}
              hint="Permet de valider la résilience et les états d'erreur."
            />

            <TextField
              id="demo-password-field"
              label="3. Mot de passe démo"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="demo"
              hint="Mode démo D1 : déterministe (laisser 'demo')."
            />
          </div>

          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
            <div className="font-semibold text-slate-800">Détails de l'identité sélectionnée :</div>
            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1">
              <span><strong>ID :</strong> {selectedIdentity.id}</span>
              <span><strong>Rôle :</strong> {selectedIdentity.role}</span>
              <span><strong>Organisation :</strong> {selectedIdentity.organizationId}</span>
              <span><strong>Portail cible :</strong> {selectedIdentity.defaultPortal}</span>
            </div>
          </div>

          <div className="mt-6 flex justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={onClose} type="button">
              Annuler
            </Button>
            <Button variant="primary" type="submit" disabled={isLoading}>
              {isLoading ? 'Connexion en cours…' : `Se connecter en tant que ${selectedIdentity.displayName}`}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
