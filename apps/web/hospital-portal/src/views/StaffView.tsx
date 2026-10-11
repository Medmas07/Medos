import { useState, type FormEvent } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  DemoBadge,
  EmptyState,
  PageHeader,
  SelectField,
  StatCard,
  StatGroup,
  Table,
  TextField,
  type TableColumn,
} from '@hackcure/design-system'
import {
  addStaff,
  EMPTY_STAFF_INPUT,
  filterStaff,
  ROLE_LABELS,
  setStaffStatus,
  staffDisplayName,
  validateStaff,
  type StaffErrors,
  type StaffInput,
  type StaffMember,
  type StaffRole,
} from '../services/staffService'

interface StaffViewProps {
  staff: readonly StaffMember[]
  onChange: (staff: StaffMember[]) => void
}

const ROLE_OPTIONS = (Object.keys(ROLE_LABELS) as StaffRole[]).map((value) => ({ value, label: ROLE_LABELS[value] }))

export function StaffView({ staff, onChange }: StaffViewProps) {
  const [query, setQuery] = useState('')
  const [role, setRole] = useState<StaffRole | ''>('')
  const [adding, setAdding] = useState(false)

  const active = staff.filter((s) => s.status === 'active')
  const rows = filterStaff(staff, query, role)

  const columns: TableColumn<StaffMember>[] = [
    { key: 'name', header: 'Nom', rowHeader: true, render: (s) => <span className="font-medium text-ink">{staffDisplayName(s)}</span> },
    { key: 'role', header: 'Rôle', render: (s) => <Badge tone={s.role === 'physician' ? 'info' : 'neutral'}>{ROLE_LABELS[s.role]}</Badge> },
    { key: 'specialty', header: 'Spécialité / service', render: (s) => s.specialty },
    {
      key: 'status',
      header: 'Statut',
      render: (s) => (
        <Badge tone={s.status === 'active' ? 'success' : 'neutral'} dot>
          {s.status === 'active' ? 'Actif' : 'Inactif'}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: <span className="sr-only">Actions</span>,
      align: 'right',
      render: (s) => (
        <Button
          size="sm"
          variant="ghost"
          onClick={() => onChange(setStaffStatus(staff, s.id, s.status === 'active' ? 'inactive' : 'active'))}
        >
          {s.status === 'active' ? 'Désactiver' : 'Réactiver'}
        </Button>
      ),
    },
  ]

  return (
    <>
      <PageHeader
        eyebrow="Ressources humaines"
        title="Gestion du personnel"
        description="Médecins, infirmiers et personnel administratif de l'établissement."
        actions={
          <>
            <DemoBadge>Données fictives</DemoBadge>
            {!adding && <Button onClick={() => setAdding(true)}>Ajouter un membre</Button>}
          </>
        }
      />
      <div className="space-y-6">
        <StatGroup columns={3}>
          <StatCard label="Personnel actif" value={active.length} hint={`${staff.length} au total`} />
          <StatCard label="Médecins" value={active.filter((s) => s.role === 'physician').length} hint="Actifs" />
          <StatCard label="Infirmiers" value={active.filter((s) => s.role === 'nurse').length} hint="Actifs" />
        </StatGroup>

        {adding && (
          <StaffForm
            onCancel={() => setAdding(false)}
            onSubmit={(input) => {
              onChange(addStaff(staff, input))
              setAdding(false)
            }}
          />
        )}

        <Card title="Personnel" description="Les modifications sont conservées en mémoire jusqu'au rechargement de la page.">
          <div className="mb-4 grid gap-3 sm:grid-cols-[1fr_14rem]">
            <TextField label="Rechercher" placeholder="Nom, spécialité…" value={query} onChange={(e) => setQuery(e.target.value)} />
            <SelectField
              label="Rôle"
              placeholder="Tous les rôles"
              options={ROLE_OPTIONS}
              value={role}
              onChange={(e) => setRole(e.target.value as StaffRole | '')}
            />
          </div>
          <Table
            caption="Liste du personnel"
            columns={columns}
            rows={rows}
            getRowKey={(s) => s.id}
            empty={<EmptyState title="Aucun membre trouvé" description="Modifiez la recherche ou le filtre de rôle." />}
          />
        </Card>
      </div>
    </>
  )
}

function StaffForm({ onSubmit, onCancel }: { onSubmit: (input: StaffInput) => void; onCancel: () => void }) {
  const [input, setInput] = useState<StaffInput>(EMPTY_STAFF_INPUT)
  const [errors, setErrors] = useState<StaffErrors>({})

  const field = (key: keyof StaffInput) => ({
    value: input[key],
    error: errors[key],
    onChange: (e: { target: { value: string } }) => setInput({ ...input, [key]: e.target.value }),
  })

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const found = validateStaff(input)
    setErrors(found)
    if (Object.keys(found).length === 0) onSubmit(input)
  }

  return (
    <Card title="Nouveau membre du personnel">
      <form onSubmit={submit} noValidate className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-[8rem_1fr_1fr]">
          <TextField label="Titre" placeholder="Dr, Pr…" {...field('title')} />
          <TextField label="Prénom" required {...field('firstName')} />
          <TextField label="Nom" required {...field('lastName')} />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField label="Rôle" required placeholder="Choisir…" options={ROLE_OPTIONS} {...field('role')} />
          <TextField label="Spécialité / service" required {...field('specialty')} />
        </div>
        <Alert tone="info" title="Aucun compte n'est créé">
          L'ajout n'ouvre aucun accès au système : la gestion des comptes et des droits n'est pas encore implémentée.
        </Alert>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onCancel}>
            Annuler
          </Button>
          <Button type="submit">Ajouter</Button>
        </div>
      </form>
    </Card>
  )
}
