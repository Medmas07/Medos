import { useEffect, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import {
  Alert,
  AppShell,
  Badge,
  Button,
  Card,
  CheckboxField,
  DemoBadge,
  DemoBanner,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  SelectField,
  SideNav,
  Skeleton,
  Spinner,
  StatCard,
  Table,
  TextareaField,
  TextField,
  ThemeToggle,
  Timeline,
} from '../src'
import type { TableColumn, Tone } from '../src'
import { placeholderRequests } from './placeholder-data'
import type { PlaceholderRequest } from './placeholder-data'

const sections = [
  { id: 'typography', label: 'Typography' },
  { id: 'colors', label: 'Colors' },
  { id: 'spacing', label: 'Spacing' },
  { id: 'buttons', label: 'Buttons' },
  { id: 'forms', label: 'Forms' },
  { id: 'cards', label: 'Cards' },
  { id: 'tables', label: 'Tables' },
  { id: 'badges', label: 'Badges' },
  { id: 'alerts', label: 'Alerts' },
  { id: 'states', label: 'States' },
  { id: 'timeline', label: 'Timeline' },
] as const

function useHash() {
  const [hash, setHash] = useState(() => window.location.hash)
  useEffect(() => {
    const onChange = () => setHash(window.location.hash)
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return hash
}

export function App() {
  const hash = useHash()
  const current = hash.slice(1) || sections[0].id

  return (
    <AppShell
      banner={<DemoBanner />}
      productName="Design System"
      productContext="HC-004 · web portals"
      navigation={
        <SideNav
          label="Showcase sections"
          sections={[
            {
              title: 'Foundations',
              items: sections.slice(0, 3).map((s) => ({
                label: s.label,
                href: `#${s.id}`,
                current: current === s.id,
              })),
            },
            {
              title: 'Components',
              items: sections.slice(3).map((s) => ({
                label: s.label,
                href: `#${s.id}`,
                current: current === s.id,
              })),
            },
          ]}
        />
      }
      sidebarFooter={<DemoBadge>Placeholder content</DemoBadge>}
      toolbar={<ThemeToggle labels={{ system: 'System theme', light: 'Light theme', dark: 'Dark theme' }} label="Theme" />}
    >
      <div className="mx-auto max-w-5xl">
        <PageHeader
          eyebrow="@hackcure/design-system"
          title="Visual design system"
          description="Shared tokens and React components for the Hospital, Governance, and Research portals. All content on this page is fictional placeholder text."
          actions={<Badge tone="info">D1</Badge>}
        />
        <div className="space-y-12">
          <TypographySection />
          <ColorsSection />
          <SpacingSection />
          <ButtonsSection />
          <FormsSection />
          <CardsSection />
          <TablesSection />
          <BadgesSection />
          <AlertsSection />
          <StatesSection />
          <TimelineSection />
        </div>
      </div>
    </AppShell>
  )
}

function Section({
  id,
  title,
  description,
  children,
}: {
  id: string
  title: string
  description: string
  children: ReactNode
}) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="scroll-mt-6">
      <h2 id={`${id}-title`}>{title}</h2>
      <p className="mb-4 text-ink-soft">{description}</p>
      {children}
    </section>
  )
}

function TypographySection() {
  return (
    <Section
      id="typography"
      title="Typography"
      description="Geist for the interface, Instrument Serif for page titles and key figures; headings are styled globally by theme.css."
    >
      <Card>
        <div className="space-y-3">
          <h1>Heading 1 · Page title</h1>
          <h2>Heading 2 · Section title</h2>
          <h3>Heading 3 · Group title</h3>
          <h4>Heading 4 · Overline</h4>
          <p>
            Body text is 14px with a 24px line height, sized for dense review screens. Use{' '}
            <code>code</code> for identifiers such as <code>SR-0101</code>.
          </p>
          <p className="text-xs text-ink-muted">Small text for hints, metadata, and captions.</p>
        </div>
      </Card>
    </Section>
  )
}

const swatchGroups: { name: string; note: string; swatches: { step: string; className: string }[] }[] = [
  {
    name: 'brand',
    note: 'Mint #A7E3D4 = 300. 700 text on white, 800 solid fill, 300 highlights',
    swatches: [
      { step: '50', className: 'bg-brand-50' },
      { step: '100', className: 'bg-brand-100' },
      { step: '200', className: 'bg-brand-200' },
      { step: '300', className: 'bg-brand-300' },
      { step: '400', className: 'bg-brand-400' },
      { step: '500', className: 'bg-brand-500' },
      { step: '600', className: 'bg-brand-600' },
      { step: '700', className: 'bg-brand-700' },
      { step: '800', className: 'bg-brand-800' },
      { step: '900', className: 'bg-brand-900' },
      { step: '950', className: 'bg-brand-950' },
    ],
  },
  {
    name: 'neutrals',
    note: 'paper, surface, surface-muted, line, line-strong, ink-muted, ink-soft, ink (flip per theme)',
    swatches: [
      { step: 'paper', className: 'bg-paper' },
      { step: 'surface', className: 'bg-surface' },
      { step: 'muted', className: 'bg-surface-muted' },
      { step: 'line', className: 'bg-line' },
      { step: 'strong', className: 'bg-line-strong' },
      { step: 'ink-m', className: 'bg-ink-muted' },
      { step: 'ink-s', className: 'bg-ink-soft' },
      { step: 'ink', className: 'bg-ink' },
    ],
  },
  ...(
    [
      ['info', 'Informational, in progress', ['bg-info-50', 'bg-info-200', 'bg-info-600', 'bg-info-700']],
      ['success', 'Completed, approved', ['bg-success-50', 'bg-success-200', 'bg-success-600', 'bg-success-700']],
      ['warning', 'Needs attention, pending', ['bg-warning-50', 'bg-warning-200', 'bg-warning-600', 'bg-warning-700']],
      ['danger', 'Error, rejected, destructive', ['bg-danger-50', 'bg-danger-200', 'bg-danger-600', 'bg-danger-700']],
      ['demo', 'MOCKED / fictional content only', ['bg-demo-50', 'bg-demo-200', 'bg-demo-600', 'bg-demo-700']],
    ] as const
  ).map(([name, note, classes]) => ({
    name,
    note,
    swatches: classes.map((className, i) => ({ step: ['50', '200', '600', '700'][i], className })),
  })),
]

function ColorsSection() {
  return (
    <Section
      id="colors"
      title="Colors"
      description="Brand, neutral, and status tones are CSS custom properties with light and dark values. Toggle the theme in the sidebar to compare."
    >
      <Card>
        <div className="space-y-4">
          {swatchGroups.map((group) => (
            <div key={group.name} className="grid gap-2 sm:grid-cols-[10rem_1fr] sm:items-center">
              <div>
                <p className="font-medium text-ink">
                  <code>{group.name}</code>
                </p>
                <p className="text-xs text-ink-muted">{group.note}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {group.swatches.map((swatch) => (
                  <div key={swatch.step} className="text-center">
                    <div
                      className={`h-10 w-14 rounded-md ring-1 ring-ink/10 ring-inset ${swatch.className}`}
                    />
                    <span className="text-xs text-ink-muted">{swatch.step}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </Section>
  )
}

const spacingSteps = [
  { token: '1', px: 4, className: 'w-1' },
  { token: '2', px: 8, className: 'w-2' },
  { token: '3', px: 12, className: 'w-3' },
  { token: '4', px: 16, className: 'w-4' },
  { token: '6', px: 24, className: 'w-6' },
  { token: '8', px: 32, className: 'w-8' },
  { token: '12', px: 48, className: 'w-12' },
  { token: '16', px: 64, className: 'w-16' },
]

function SpacingSection() {
  return (
    <Section
      id="spacing"
      title="Spacing"
      description="Tailwind's 4px scale. Prefer 2–4 inside components, 4–6 between related blocks, and 8–12 between page sections."
    >
      <Card>
        <ul className="space-y-2">
          {spacingSteps.map((step) => (
            <li key={step.token} className="flex items-center gap-4">
              <code className="w-8 text-right text-ink-muted">{step.token}</code>
              <span className={`h-4 rounded-sm bg-brand-500 ${step.className}`} />
              <span className="text-xs text-ink-muted">{step.px}px</span>
            </li>
          ))}
        </ul>
      </Card>
    </Section>
  )
}

function ButtonsSection() {
  const [saving, setSaving] = useState(false)

  function simulateSave() {
    setSaving(true)
    window.setTimeout(() => setSaving(false), 1500)
  }

  return (
    <Section
      id="buttons"
      title="Buttons"
      description="One primary action per view. Danger is reserved for destructive or rejecting actions."
    >
      <Card>
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <Button>Primary</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="danger">Reject</Button>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button size="sm">Small primary</Button>
            <Button size="sm" variant="secondary">
              Small secondary
            </Button>
            <Button disabled>Disabled</Button>
            <Button loading={saving} onClick={simulateSave}>
              {saving ? 'Saving…' : 'Simulate save'}
            </Button>
          </div>
        </div>
      </Card>
    </Section>
  )
}

const purposeOptions = [
  { value: 'continuity', label: 'Continuity of care' },
  { value: 'research', label: 'Approved research' },
  { value: 'audit', label: 'Governance audit' },
]

function FormsSection() {
  const [organization, setOrganization] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [showErrors, setShowErrors] = useState(false)
  const organizationError =
    showErrors && organization.trim() === '' ? 'Enter the organization name.' : undefined

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setShowErrors(true)
    setSubmitted(organization.trim() !== '')
  }

  return (
    <Section
      id="forms"
      title="Forms"
      description="Labels are always visible; hints and errors are linked to their control. Submit the form empty to see validation."
    >
      <Card>
        <form noValidate onSubmit={handleSubmit} className="grid gap-5 md:grid-cols-2">
          <TextField
            label="Organization name"
            required
            placeholder="e.g. Hospital A"
            hint="As registered with the Governance / Ethics Authority."
            value={organization}
            onChange={(event) => {
              setOrganization(event.target.value)
              setSubmitted(false)
            }}
            error={organizationError}
          />
          <SelectField
            label="Purpose"
            placeholder="Select a purpose"
            options={purposeOptions}
            defaultValue=""
          />
          <TextareaField
            className="md:col-span-2"
            label="Justification"
            hint="Explain why access is needed and for how long."
          />
          <TextField label="Disabled field" value="Read-only value" disabled readOnly />
          <TextField label="Field with error" defaultValue="2026-13-45" error="Enter a valid date." />
          <CheckboxField
            className="md:col-span-2"
            label="I confirm this request contains fictional data only"
            hint="Showcase checkbox; it does not affect submission."
          />
          <div className="flex gap-3 md:col-span-2">
            <Button type="submit">Submit</Button>
            <Button
              variant="ghost"
              onClick={() => {
                setOrganization('')
                setShowErrors(false)
                setSubmitted(false)
              }}
            >
              Reset
            </Button>
          </div>
          {submitted && (
            <Alert tone="demo" title="Demo only — nothing was sent" className="md:col-span-2">
              The showcase form has no backend. Portals submit through explicit API contracts.
            </Alert>
          )}
        </form>
      </Card>
    </Section>
  )
}

function CardsSection() {
  return (
    <Section
      id="cards"
      title="Cards"
      description="Group related content. Optional header actions and footer."
    >
      <div className="hc-stagger mb-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Pending approvals" value={3} hint="Awaiting a governance decision" badge={<Badge tone="warning" dot>Review</Badge>} onClick={() => undefined} />
        <StatCard label="Hospital Nodes" value={12} hint="10 online · 2 offline" tone="success" />
        <StatCard label="Ledger proofs" value={48} hint="Simulated anchoring" badge={<DemoBadge>Simulated</DemoBadge>} />
        <StatCard label="Loading figure" value="—" hint="Skeleton while data loads" loading />
      </div>
      <div className="hc-stagger grid gap-4 md:grid-cols-3">
        <Card title="Pending approvals" description="Awaiting a governance decision" interactive>
          <p className="tabular font-display text-4xl text-ink">3</p>
        </Card>
        <Card
          title="Hospital Node"
          description="Hospital A"
          actions={<Badge tone="success" dot>Online</Badge>}
          footer={<span className="text-xs text-ink-muted">Last check 2 minutes ago (simulated)</span>}
        >
          <p className="text-ink-soft">Version 0.1.0 · DMI adapter: mocked</p>
        </Card>
        <Card>
          <p className="text-ink-soft">A card without a header is a plain surface.</p>
        </Card>
      </div>
    </Section>
  )
}

const requestColumns: readonly TableColumn<PlaceholderRequest>[] = [
  { key: 'reference', header: 'Reference', rowHeader: true, render: (r) => <code>{r.reference}</code> },
  { key: 'kind', header: 'Type', render: (r) => r.kind },
  { key: 'requester', header: 'Requester', render: (r) => r.requester },
  { key: 'submitted', header: 'Submitted', render: (r) => r.submitted },
  {
    key: 'status',
    header: 'Status',
    align: 'right',
    render: (r) => (
      <Badge tone={r.status.tone} dot>
        {r.status.label}
      </Badge>
    ),
  },
]

type TableDemoState = 'data' | 'loading' | 'empty' | 'error'

function TablesSection() {
  const [state, setState] = useState<TableDemoState>('data')

  const stateButtons: { value: TableDemoState; label: string }[] = [
    { value: 'data', label: 'Data' },
    { value: 'loading', label: 'Loading' },
    { value: 'empty', label: 'Empty' },
    { value: 'error', label: 'Error' },
  ]

  return (
    <Section
      id="tables"
      title="Tables"
      description="Every data view needs loading, empty, and error states. Switch between them below."
    >
      <Card
        title="Requests"
        description="Placeholder rows"
        flush
        actions={
          <div role="group" aria-label="Table state" className="flex gap-1">
            {stateButtons.map((option) => (
              <Button
                key={option.value}
                size="sm"
                variant={state === option.value ? 'primary' : 'secondary'}
                aria-pressed={state === option.value}
                onClick={() => setState(option.value)}
              >
                {option.label}
              </Button>
            ))}
          </div>
        }
      >
        {state === 'loading' && <LoadingState label="Loading requests…" />}
        {state === 'error' && (
          <ErrorState
            title="Requests could not be loaded"
            description="The governance service did not respond (simulated)."
            action={
              <Button size="sm" variant="secondary" onClick={() => setState('data')}>
                Retry
              </Button>
            }
          />
        )}
        {(state === 'data' || state === 'empty') && (
          <Table
            caption="Placeholder governance requests"
            columns={requestColumns}
            rows={state === 'data' ? placeholderRequests : []}
            getRowKey={(r) => r.reference}
            empty={
              <EmptyState
                title="No requests yet"
                description="New hospital, synchronization, and research requests will appear here."
              />
            }
          />
        )}
      </Card>
    </Section>
  )
}

const tones: Tone[] = ['neutral', 'info', 'success', 'warning', 'danger', 'demo']

function BadgesSection() {
  return (
    <Section
      id="badges"
      title="Badges"
      description="Short statuses. Portals map their own domain statuses to a tone; the text always carries the meaning."
    >
      <Card>
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {tones.map((tone) => (
              <Badge key={tone} tone={tone}>
                {tone}
              </Badge>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            {tones.map((tone) => (
              <Badge key={tone} tone={tone} dot>
                {tone} with dot
              </Badge>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            <DemoBadge />
            <DemoBadge>Simulated proof</DemoBadge>
            <DemoBadge>Mock AI output</DemoBadge>
          </div>
        </div>
      </Card>
    </Section>
  )
}

function AlertsSection() {
  return (
    <Section
      id="alerts"
      title="Alerts"
      description="Warning and danger alerts are announced to screen readers immediately."
    >
      <div className="space-y-3">
        <Alert tone="info" title="Request submitted">
          The Governance / Ethics Authority will review it. You will be notified of the decision.
        </Alert>
        <Alert tone="success" title="Synchronization approved" />
        <Alert
          tone="warning"
          title="Authorization expires in 2 days"
          actions={
            <Button size="sm" variant="secondary">
              Request renewal
            </Button>
          }
        />
        <Alert tone="danger" title="Submission failed">
          The document upload was rejected. Check the file type and try again.
        </Alert>
        <Alert tone="demo" title="Simulated behaviour">
          This result comes from a deterministic mock and is not production data.
        </Alert>
      </div>
    </Section>
  )
}

function StatesSection() {
  return (
    <Section
      id="states"
      title="States"
      description="Use these instead of blank areas so users always know what is happening."
    >
      <div className="grid gap-4 md:grid-cols-3">
        <Card title="Loading">
          <LoadingState />
        </Card>
        <Card title="Empty">
          <EmptyState
            title="No notifications"
            description="You're all caught up."
            action={
              <Button size="sm" variant="secondary">
                Refresh
              </Button>
            }
          />
        </Card>
        <Card title="Error">
          <ErrorState description="Try again in a moment." />
        </Card>
      </div>
      <Card title="Skeleton loading" description='LoadingState variant="skeleton" sketches the page while keeping a status label.' className="mt-4">
        <LoadingState variant="skeleton" label="Loading page…" />
      </Card>
      <div className="mt-4 flex flex-wrap gap-3">
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-4 w-24" />
      </div>
      <p className="mt-4 flex items-center gap-2 text-ink-soft">
        <Spinner size="sm" className="text-brand-600" /> Inline spinner for compact pending states.
      </p>
    </Section>
  )
}

function TimelineSection() {
  return (
    <Section
      id="timeline"
      title="Timeline"
      description="Chronological events or process steps. Mark the in-progress step as current."
    >
      <div className="grid gap-4 md:grid-cols-2">
        <Card title="Request history" description="Placeholder synchronization request">
          <Timeline
            label="Request history"
            items={[
              {
                id: 'submitted',
                title: 'Request submitted',
                timestamp: '08 Oct 2026, 09:12',
                dateTime: '2026-10-08T09:12',
                description: 'Hospital A requested synchronization with Hospital B.',
                tone: 'info',
              },
              {
                id: 'scope',
                title: 'Scope and consent checked',
                timestamp: '08 Oct 2026, 09:13',
                dateTime: '2026-10-08T09:13',
                tone: 'success',
              },
              {
                id: 'review',
                title: 'Governance review',
                timestamp: 'In progress',
                tone: 'warning',
                current: true,
              },
              {
                id: 'proof',
                title: 'Decision proof recorded',
                timestamp: 'Pending',
                tone: 'neutral',
                meta: <DemoBadge>Simulated proof</DemoBadge>,
              },
            ]}
          />
        </Card>
        <Card title="Execution stages" description="Placeholder compute-to-data job">
          <Timeline
            label="Execution stages"
            items={[
              { id: 'auth', title: 'Authorization verified', timestamp: '10:00', tone: 'success' },
              { id: 'a', title: 'Hospital A executing', timestamp: '10:01', tone: 'success' },
              {
                id: 'b',
                title: 'Hospital B executing',
                timestamp: 'Running',
                tone: 'info',
                current: true,
              },
              { id: 'agg', title: 'Aggregating results', timestamp: 'Waiting', tone: 'neutral' },
            ]}
          />
        </Card>
      </div>
    </Section>
  )
}
