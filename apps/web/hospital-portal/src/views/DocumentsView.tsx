import { useRef, useState, type ChangeEvent } from 'react'
import { Alert, Badge, Button, Card, DemoBadge, EmptyState, PageHeader, type Tone } from '@hackcure/design-system'
import { formatDateTime } from '../presentation'
import {
  ACCEPT_ATTRIBUTE,
  applyRemoval,
  applyUpload,
  canRemove,
  canUpload,
  documentChecklist,
  formatSize,
  REQUIRED_DOCUMENTS,
  uploadDocument,
  validateFile,
  type FileDescription,
} from '../services/documentService'
import type { ApplicationDocument, HospitalApplication, OnboardingSnapshot, StepId } from '../types/onboarding'

interface DocumentsViewProps {
  snapshot: OnboardingSnapshot
  /** Returns true once when the demo scenario should make this upload fail. */
  consumeSimulatedFailure: () => boolean
  onUpdated: (snapshot: OnboardingSnapshot) => void
  onNavigate: (step: StepId) => void
}

const documentStatus: Record<ApplicationDocument['status'], { label: string; tone: Tone }> = {
  received: { label: 'Reçu', tone: 'success' },
  missing: { label: 'À fournir', tone: 'warning' },
  rejected: { label: 'Refusé', tone: 'danger' },
}

export function DocumentsView({ snapshot, consumeSimulatedFailure, onUpdated, onNavigate }: DocumentsViewProps) {
  const { application } = snapshot
  const header = (
    <PageHeader
      eyebrow="Étape 3 · Parcours d'adhésion"
      title="Documents administratifs"
      description="Pièces justificatives de votre établissement, examinées lors de la revue de votre candidature."
      actions={<DemoBadge>Dépôt simulé</DemoBadge>}
    />
  )

  if (!application) {
    return (
      <>
        {header}
        <Card>
          <EmptyState
            title="Aucune inscription"
            description="Inscrivez d'abord votre établissement pour déposer ses documents."
            action={<Button onClick={() => onNavigate('registration')}>Aller à l'inscription</Button>}
          />
        </Card>
      </>
    )
  }

  const checklist = documentChecklist(application)
  const received = checklist.filter((d) => d.status === 'received').length
  const complete = received === checklist.length
  const underReview = application.status === 'pending' || application.status === 'human_review'
  const approved = application.status === 'approved'
  const locked = application.status === 'rejected' || (approved && complete)

  return (
    <>
      {header}
      <div className="space-y-6">
        <Alert tone="demo" title="Démonstration : aucun fichier n'est transmis">
          Le contenu du fichier n'est ni lu ni envoyé ; seuls son nom, sa taille et son format sont conservés dans
          cette page jusqu'à son rechargement. N'utilisez que des documents fictifs.
        </Alert>
        {underReview && !complete && (
          <Alert tone="warning" title="Complément attendu">
            Votre candidature est en revue. Vous pouvez encore fournir les pièces manquantes ; les pièces reçues ne
            peuvent plus être remplacées.
          </Alert>
        )}
        {approved && !complete && (
          <Alert tone="warning" title="Pièces à fournir après approbation">
            L'adhésion est approuvée ; les pièces manquantes restent à fournir, notamment si les conditions de la
            décision l'exigent. Les pièces reçues ne peuvent plus être remplacées.
          </Alert>
        )}
        {locked && (
          <Alert tone="neutral" title="Documents verrouillés">
            La candidature a reçu une décision de l'Autorité de gouvernance : les documents ne peuvent plus être
            modifiés.
          </Alert>
        )}
        {complete && application.status === 'draft' && (
          <Alert
            tone="success"
            title="Toutes les pièces sont déposées"
            actions={<Button onClick={() => onNavigate('agreements')}>Continuer : accords</Button>}
          >
            Les documents seront examinés lors de la revue de votre candidature.
          </Alert>
        )}

        <Card
          title="Pièces justificatives"
          description="PDF, JPEG ou PNG, 10 Mo au maximum."
          actions={<Badge tone={complete ? 'success' : 'neutral'}>{`${received} / ${checklist.length} reçues`}</Badge>}
          flush
        >
          <ul className="divide-y divide-slate-200">
            {checklist.map((document) => (
              <DocumentRow
                key={document.type}
                application={application}
                document={document}
                consumeSimulatedFailure={consumeSimulatedFailure}
                onUploaded={(upload) => onUpdated(applyUpload(snapshot, document.type, upload))}
                onRemove={() => onUpdated(applyRemoval(snapshot, document.type))}
              />
            ))}
          </ul>
        </Card>
      </div>
    </>
  )
}

type RowState =
  | { kind: 'idle' }
  | { kind: 'uploading'; fileName: string; percent: number }
  | { kind: 'invalid'; message: string }
  | { kind: 'failed'; message: string; file: FileDescription }

function DocumentRow({
  application,
  document,
  consumeSimulatedFailure,
  onUploaded,
  onRemove,
}: {
  application: HospitalApplication
  document: ApplicationDocument
  consumeSimulatedFailure: () => boolean
  onUploaded: (upload: NonNullable<ApplicationDocument['upload']>) => void
  onRemove: () => void
}) {
  const input = useRef<HTMLInputElement>(null)
  const [state, setState] = useState<RowState>({ kind: 'idle' })
  const required = REQUIRED_DOCUMENTS.find((r) => r.type === document.type)!
  const status = documentStatus[document.status]
  const uploadable = canUpload(application, document)
  const busy = state.kind === 'uploading'

  const start = async (file: FileDescription) => {
    const invalid = validateFile(file)
    if (invalid) {
      setState({ kind: 'invalid', message: invalid })
      return
    }
    setState({ kind: 'uploading', fileName: file.name, percent: 0 })
    try {
      const upload = await uploadDocument(file, {
        simulateFailure: consumeSimulatedFailure(),
        onProgress: (percent) => setState({ kind: 'uploading', fileName: file.name, percent }),
      })
      setState({ kind: 'idle' })
      onUploaded(upload)
    } catch (error) {
      setState({ kind: 'failed', message: error instanceof Error ? error.message : String(error), file })
    }
  }

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (file) void start({ name: file.name, size: file.size, type: file.type })
  }

  return (
    <li className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-slate-900">{required.label}</span>
          <Badge tone={status.tone}>{status.label}</Badge>
          {document.upload && <DemoBadge>Dépôt local</DemoBadge>}
        </div>
        {document.status === 'received' ? (
          <p className="text-sm break-words text-slate-600">
            {document.upload
              ? `${document.upload.fileName} · ${formatSize(document.upload.sizeBytes)} · déposé le ${formatDateTime(document.upload.uploadedAt)}`
              : document.title}
          </p>
        ) : (
          <p className="text-sm text-slate-500">{required.hint}</p>
        )}

        {state.kind === 'uploading' && (
          <div className="space-y-1 pt-1">
            <p className="text-xs text-slate-600">Envoi simulé de {state.fileName}…</p>
            <div
              role="progressbar"
              aria-label={`Envoi de ${required.label}`}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={state.percent}
              className="h-1.5 w-full max-w-xs overflow-hidden rounded-full bg-slate-200"
            >
              <div className="h-full bg-brand-600 transition-[width]" style={{ width: `${state.percent}%` }} />
            </div>
          </div>
        )}
        {state.kind === 'invalid' && <p className="text-xs font-medium text-danger-700">{state.message}</p>}
        {state.kind === 'failed' && (
          <p className="text-xs font-medium text-danger-700">{state.message} Le fichier n'a pas été enregistré.</p>
        )}
      </div>

      <div className="flex shrink-0 flex-wrap gap-2">
        {uploadable && (
          <input
            ref={input}
            type="file"
            accept={ACCEPT_ATTRIBUTE}
            aria-label={`Fichier : ${required.label}`}
            className="sr-only"
            tabIndex={-1}
            disabled={busy}
            onChange={handleChange}
          />
        )}
        {state.kind === 'failed' && (
          <Button size="sm" variant="secondary" onClick={() => void start(state.file)}>
            Réessayer
          </Button>
        )}
        {uploadable && (
          <Button
            size="sm"
            variant={document.status === 'received' ? 'secondary' : 'primary'}
            loading={busy}
            onClick={() => input.current?.click()}
          >
            {document.status === 'received' ? 'Remplacer' : 'Déposer'}
          </Button>
        )}
        {canRemove(application, document) && !busy && (
          <Button size="sm" variant="ghost" onClick={onRemove}>
            Retirer
          </Button>
        )}
      </div>
    </li>
  )
}
