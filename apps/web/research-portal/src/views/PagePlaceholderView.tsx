import { Alert, Badge, Card, EmptyState, PageHeader } from '@hackcure/design-system'
import { pageStatusDisplay } from '../presentation'
import type { PortalPage } from '../types/research'

interface PagePlaceholderViewProps {
  page: PortalPage
  section: string
}

/** Frame for a page whose content is delivered by a later ticket (HC-091 to HC-102). */
export function PagePlaceholderView({ page, section }: PagePlaceholderViewProps) {
  const display = pageStatusDisplay[page.status]
  return (
    <>
      <PageHeader
        eyebrow={`${section} · ${page.ticket}`}
        title={page.label}
        actions={<Badge tone={display.tone}>{display.label}</Badge>}
      />
      {page.status === 'locked' && (
        <Alert tone="neutral" title="Page verrouillée" className="mb-6">
          {page.detail}
        </Alert>
      )}
      <Card>
        <EmptyState
          title={`Écran prévu par ${page.ticket}`}
          description={
            "Le shell du portail (HC-090) réserve cette page ; son contenu n'est pas encore implémenté." +
            (page.status === 'available' ? ` Données de démonstration : ${page.detail}` : '')
          }
        />
      </Card>
    </>
  )
}
