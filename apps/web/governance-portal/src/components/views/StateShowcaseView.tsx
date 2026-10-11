import { useState } from 'react'
import {
  Alert,
  Button,
  Card,
  DemoBadge,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
} from '@hackcure/design-system'

export function StateShowcaseView() {
  const [activeState, setActiveState] = useState<'normal' | 'loading' | 'empty' | 'error'>('normal')

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Validation Démonstration D1"
        title="Démonstrateur d'États Résilients de l'Interface"
        description="Vérification des états d'attente (Loading), d'absence de données (Empty) et de rupture de service (Error) imposés par les critères d'acceptation HC-070."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant={activeState === 'normal' ? 'primary' : 'secondary'}
              onClick={() => setActiveState('normal')}
            >
              État Normal
            </Button>
            <Button
              size="sm"
              variant={activeState === 'loading' ? 'primary' : 'secondary'}
              onClick={() => setActiveState('loading')}
            >
              Chargement
            </Button>
            <Button
              size="sm"
              variant={activeState === 'empty' ? 'primary' : 'secondary'}
              onClick={() => setActiveState('empty')}
            >
              File Vide
            </Button>
            <Button
              size="sm"
              variant={activeState === 'error' ? 'primary' : 'secondary'}
              onClick={() => setActiveState('error')}
            >
              Erreur Réseau
            </Button>
          </div>
        }
      />

      <Alert tone="info" title="Critères d'acceptation D1">
        Chaque vue de données doit intégrer une gestion explicite des états transitoires et des cas d'erreur réseau pour garantir une expérience utilisateur cohérente.
      </Alert>

      <Card
        title="Surface de Rendu selon l'État Sélectionné"
        actions={<DemoBadge>Contrôle Interactif</DemoBadge>}
      >
        {activeState === 'normal' && (
          <div className="space-y-3 py-6 text-center">
            <div className="inline-flex size-12 items-center justify-center rounded-full bg-success-50 text-success-700 font-bold">
              ✓
            </div>
            <h3 className="font-semibold text-slate-900">Fonctionnement Nominal (D1 Fixtures)</h3>
            <p className="mx-auto max-w-md text-xs text-slate-600">
              Toutes les données canoniques de gouvernance sont chargées et consultables dans les onglets dédiés.
            </p>
          </div>
        )}

        {activeState === 'loading' && (
          <div className="py-8">
            <LoadingState label="Interrogation du Nœud de Gouvernance et vérification des contrats d'échange..." />
          </div>
        )}

        {activeState === 'empty' && (
          <div className="py-8">
            <EmptyState
              title="Aucune demande en attente d'instruction"
              description="Tous les dossiers d'adhésion et de synchronisation pour ce filtre ont été arbitrés par le réviseur de gouvernance."
              action={
                <Button size="sm" onClick={() => setActiveState('normal')}>
                  Réinitialiser les filtres
                </Button>
              }
            />
          </div>
        )}

        {activeState === 'error' && (
          <div className="py-8">
            <ErrorState
              title="Connexion au Nœud de Gouvernance interrompue"
              description="Impossible de joindre le port RPC de l'instance de gouvernance. Aucun accès direct à une base de données n'est toléré en mode dégradé."
              action={
                <Button size="sm" onClick={() => setActiveState('normal')}>
                  Réessayer la connexion
                </Button>
              }
            />
          </div>
        )}
      </Card>
    </div>
  )
}
