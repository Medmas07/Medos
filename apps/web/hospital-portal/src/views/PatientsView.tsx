import { useState, type FormEvent } from 'react'
import {
  Alert,
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
  addPatient,
  ageOn,
  EMPTY_PATIENT_INPUT,
  filterPatients,
  SEX_LABELS,
  todayIso,
  validatePatient,
  type Patient,
  type PatientErrors,
  type PatientInput,
  type Sex,
} from '../services/patientService'

interface PatientsViewProps {
  patients: readonly Patient[]
  onChange: (patients: Patient[]) => void
}

const SEX_OPTIONS = (Object.keys(SEX_LABELS) as Sex[]).map((value) => ({ value, label: SEX_LABELS[value] }))

const dateFormat = new Intl.DateTimeFormat('fr-TN', { dateStyle: 'medium', timeZone: 'UTC' })

export function PatientsView({ patients, onChange }: PatientsViewProps) {
  const [query, setQuery] = useState('')
  const [adding, setAdding] = useState(false)
  const today = todayIso()

  const rows = filterPatients(patients, query)
  const added = patients.filter((p) => p.id.startsWith('pat-local-')).length

  const columns: TableColumn<Patient>[] = [
    { key: 'localId', header: 'IPP', render: (p) => <code>{p.localId}</code> },
    { key: 'name', header: 'Nom', rowHeader: true, render: (p) => <span className="font-medium text-ink">{`${p.lastName.toUpperCase()} ${p.firstName}`}</span> },
    { key: 'sex', header: 'Sexe', render: (p) => SEX_LABELS[p.sex] },
    {
      key: 'birthDate',
      header: 'Naissance',
      render: (p) => `${dateFormat.format(new Date(`${p.birthDate}T00:00:00Z`))} · ${ageOn(p.birthDate, today)} ans`,
    },
    { key: 'city', header: 'Ville', render: (p) => p.city },
  ]

  return (
    <>
      <PageHeader
        eyebrow="Admissions"
        title="Gestion des patients"
        description="Identité administrative des patients de l'établissement."
        actions={
          <>
            <DemoBadge>Données fictives</DemoBadge>
            {!adding && <Button onClick={() => setAdding(true)}>Enregistrer un patient</Button>}
          </>
        }
      />
      <div className="space-y-6">
        <Alert tone="info" title="Aucune donnée clinique sur cette page">
          Seule l'identité administrative est affichée. Les dossiers cliniques restent dans le Hospital Node de
          l'établissement et n'apparaissent pas ici.
        </Alert>

        <StatGroup columns={3}>
          <StatCard label="Patients" value={patients.length} hint="Connus de l'établissement" />
          <StatCard label="Enregistrés aujourd'hui" value={added} hint="Dans cette session" />
          <StatCard label="Villes" value={new Set(patients.map((p) => p.city)).size} hint="Lieux de résidence" />
        </StatGroup>

        {adding && (
          <PatientForm
            today={today}
            onCancel={() => setAdding(false)}
            onSubmit={(input) => {
              onChange(addPatient(patients, input, today))
              setAdding(false)
            }}
          />
        )}

        <Card title="Patients" description="Les modifications sont conservées en mémoire jusqu'au rechargement de la page.">
          <div className="mb-4 max-w-md">
            <TextField label="Rechercher" placeholder="IPP, nom, ville…" value={query} onChange={(e) => setQuery(e.target.value)} />
          </div>
          <Table
            caption="Liste des patients"
            columns={columns}
            rows={rows}
            getRowKey={(p) => p.id}
            empty={<EmptyState title="Aucun patient trouvé" description="Modifiez la recherche." />}
          />
        </Card>
      </div>
    </>
  )
}

function PatientForm({
  today,
  onSubmit,
  onCancel,
}: {
  today: string
  onSubmit: (input: PatientInput) => void
  onCancel: () => void
}) {
  const [input, setInput] = useState<PatientInput>(EMPTY_PATIENT_INPUT)
  const [errors, setErrors] = useState<PatientErrors>({})

  const field = (key: keyof PatientInput) => ({
    value: input[key],
    error: errors[key],
    onChange: (e: { target: { value: string } }) => setInput({ ...input, [key]: e.target.value }),
  })

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const found = validatePatient(input, today)
    setErrors(found)
    if (Object.keys(found).length === 0) onSubmit(input)
  }

  return (
    <Card title="Nouveau patient" description="L'IPP est attribué automatiquement à l'enregistrement.">
      <form onSubmit={submit} noValidate className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="Prénom" required {...field('firstName')} />
          <TextField label="Nom" required {...field('lastName')} />
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          <SelectField label="Sexe" required placeholder="Choisir…" options={SEX_OPTIONS} {...field('sex')} />
          <TextField label="Date de naissance" type="date" required max={today} {...field('birthDate')} />
          <TextField label="Ville" required {...field('city')} />
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onCancel}>
            Annuler
          </Button>
          <Button type="submit">Enregistrer</Button>
        </div>
      </form>
    </Card>
  )
}
