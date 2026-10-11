import { useEffect, useRef, useState, type ChangeEvent } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  DemoBadge,
  EmptyState,
  PageHeader,
  SelectField,
  type Tone,
} from '@hackcure/design-system'
import { formatDateTime, requestStatusDisplay } from '../presentation'
import {
  ACCEPT_ATTRIBUTE,
  applyDocumentRemoval,
  applyDocumentUpload,
  documentChecklist,
  formatSize,
  PROJECT_DOCUMENTS,
  uploadProjectDocument,
  validateFile,
  type FileDescription,
  type ProjectDocument,
} from '../services/projectDocuments'
import { defaultDraftId, isEditableDraft } from '../services/projectCreation'
import type { DocumentUpload, PageId, ResearchSnapshot } from '../types/research'

interface ProtocolViewProps {
  snapshot: ResearchSnapshot
  /** Returns true once when the demo scenario should make this upload fail. */
  consumeSimulatedFailure: () => boolean
  onUpdated: (snapshot: ResearchSnapshot) => void
  onNavigate: (page: PageId) => void
}

const documentStatus = (document: ProjectDocument, required: boolean): { label: string; tone: Tone } =>
  document.status === 'received'
    ? { label: 'Déposé', tone: 'success' }
    : required
      ? { label: 'À fournir', tone: 'warning' }
      : { label: 'Facultatif', tone: 'neutral' }

/** Research protocol and document upload (HC-093): MOCKED, metadata kept in session state. */
export function ProtocolView({ snapshot, consumeSimulatedFailure, onUpdated, onNavigate }: ProtocolViewProps) {
  const [selectedId, setSelectedId] = useState(() => defaultDraftId(snapshot))
  const [failure, setFailure] = useState<string | null>(null)
  // Uploads finish asynchronously: each applies to the latest snapshot, so concurrent ones are all kept.
  const latest = useRef(snapshot)
  useEffect(() => {
    latest.current = snapshot
  }, [snapshot])

  const header = (
    <PageHeader
      eyebrow="Projets et demandes · HC-093"
      title="Protocole et documents"
      description="Le protocole et les pièces du projet, examinés par l'Autorité de gouvernance et d'éthique avec la demande d'accès."
      actions={<DemoBadge>Dépôt simulé</DemoBadge>}
    />
  )

  const summary = snapshot.projects.find((s) => s.project.id === selectedId) ?? snapshot.projects[0]
  if (!summary) {
    return (
      <>
        {header}
        <Card>
          <EmptyState
            title="Aucun projet de recherche"
            description="Créez d'abord un projet pour déposer son protocole."
            action={<Button onClick={() => onNavigate('new-project')}>Créer un projet</Button>}
          />
        </Card>
      </>
    )
  }

  const { project, request } = summary
  const editable = isEditableDraft(summary)
  const checklist = documentChecklist(project)
  const protocolReceived = checklist.find((d) => d.type === 'protocol')!.status === 'received'
  const requestStatus = requestStatusDisplay[request?.status ?? 'not_submitted']

  const update = (apply: (current: ResearchSnapshot) => ResearchSnapshot) => {
    try {
      setFailure(null)
      latest.current = apply(latest.current)
      onUpdated(latest.current)
    } catch (error) {
      setFailure(error instanceof Error ? error.message : String(error))
    }
  }

  return (
    <>
      {header}
      <div className="space-y-6">
        <Alert tone="demo" title="Démonstration : aucun fichier n'est transmis">
          Le contenu du fichier n'est ni lu ni envoyé ; seuls son nom, sa taille et son format sont conservés dans
          cette page jusqu'à son rechargement. N'utilisez que des documents fictifs, sans donnée de patient.
        </Alert>

        <Card>
          <SelectField
            label="Projet"
            value={project.id}
            onChange={(e) => {
              setSelectedId(e.target.value)
              setFailure(null)
            }}
            options={snapshot.projects.map((s) => ({ value: s.project.id, label: `${s.project.id} · ${s.project.title}` }))}
          />
          <p className="mt-3 flex flex-wrap items-center gap-2 text-sm text-slate-600">
            {project.status === 'draft' && <Badge tone="neutral">Brouillon</Badge>}
            <span>Demande d'accès :</span>
            <Badge tone={requestStatus.tone}>{requestStatus.label}</Badge>
          </p>
        </Card>

        {failure && (
          <Alert tone="danger" title="Le document n'a pas été modifié">
            {failure}
          </Alert>
        )}
        {!editable && (
          <Alert tone="neutral" title="Documents verrouillés">
            La demande d'accès de ce projet a été soumise à l'Autorité de gouvernance : ses documents sont examinés
            tels qu'ils ont été déposés et ne peuvent plus être modifiés.
          </Alert>
        )}
        {editable && protocolReceived && (
          <Alert
            tone="success"
            title="Protocole déposé"
            actions={<Button onClick={() => onNavigate('population')}>Continuer : population</Button>}
          >
            Déposer un document ne donne accès à aucune donnée : le protocole sera examiné avec la demande d'accès
            (HC-097).
          </Alert>
        )}
        {editable && !protocolReceived && (
          <Alert tone="info" title="Protocole attendu">
            Le protocole est requis pour soumettre la demande d'accès à l'Autorité de gouvernance.
          </Alert>
        )}

        <Card
          title="Documents du projet"
          description="PDF, 10 Mo au maximum."
          actions={<Badge tone={protocolReceived ? 'success' : 'warning'}>{protocolReceived ? 'Protocole déposé' : 'Protocole manquant'}</Badge>}
          flush
        >
          <ul className="divide-y divide-slate-200">
            {checklist.map((document) => (
              <DocumentRow
                // Resets the row's upload state when another project is selected.
                key={`${project.id}-${document.type}`}
                document={document}
                editable={editable}
                consumeSimulatedFailure={consumeSimulatedFailure}
                onUploaded={(upload) => update((current) => applyDocumentUpload(current, project.id, document.type, upload))}
                onRemove={() => update((current) => applyDocumentRemoval(current, project.id, document.type))}
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
  document,
  editable,
  consumeSimulatedFailure,
  onUploaded,
  onRemove,
}: {
  document: ProjectDocument
  editable: boolean
  consumeSimulatedFailure: () => boolean
  onUploaded: (upload: DocumentUpload) => void
  onRemove: () => void
}) {
  const input = useRef<HTMLInputElement>(null)
  const [state, setState] = useState<RowState>({ kind: 'idle' })
  const definition = PROJECT_DOCUMENTS.find((d) => d.type === document.type)!
  const status = documentStatus(document, definition.required)
  const busy = state.kind === 'uploading'
  const upload = document.document?.upload

  const start = async (file: FileDescription) => {
    const invalid = validateFile(file)
    if (invalid) {
      setState({ kind: 'invalid', message: invalid })
      return
    }
    setState({ kind: 'uploading', fileName: file.name, percent: 0 })
    try {
      const result = await uploadProjectDocument(file, {
        simulateFailure: consumeSimulatedFailure(),
        onProgress: (percent) => setState({ kind: 'uploading', fileName: file.name, percent }),
      })
      setState({ kind: 'idle' })
      onUploaded(result)
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
          <span className="font-medium text-slate-900">{definition.label}</span>
          <Badge tone={status.tone}>{status.label}</Badge>
          {upload && <DemoBadge>Dépôt local</DemoBadge>}
        </div>
        {document.document ? (
          <p className="text-sm break-words text-slate-600">
            {upload
              ? `${upload.fileName} · ${formatSize(upload.sizeBytes)} · déposé le ${formatDateTime(upload.uploadedAt)}`
              : `${document.document.title} (données de démonstration)`}
          </p>
        ) : (
          <p className="text-sm text-slate-500">{definition.hint}</p>
        )}

        {state.kind === 'uploading' && (
          <div className="space-y-1 pt-1">
            <p className="text-xs text-slate-600">Envoi simulé de {state.fileName}…</p>
            <div
              role="progressbar"
              aria-label={`Envoi de ${definition.label}`}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={state.percent}
              className="h-1.5 w-full max-w-xs overflow-hidden rounded-full bg-slate-200"
            >
              <div
                className="h-full origin-left bg-brand-600 transition-transform duration-300 ease-(--ease-out)"
                style={{ transform: `scaleX(${state.percent / 100})` }}
              />
            </div>
          </div>
        )}
        {state.kind === 'invalid' && <p className="text-xs font-medium text-danger-700">{state.message}</p>}
        {state.kind === 'failed' && (
          <p className="text-xs font-medium text-danger-700">{state.message} Le fichier n'a pas été enregistré.</p>
        )}
      </div>

      {editable && (
        <div className="flex shrink-0 flex-wrap gap-2">
          <input
            ref={input}
            type="file"
            accept={ACCEPT_ATTRIBUTE}
            aria-label={`Fichier : ${definition.label}`}
            className="sr-only"
            tabIndex={-1}
            disabled={busy}
            onChange={handleChange}
          />
          {state.kind === 'failed' && (
            <Button size="sm" variant="secondary" onClick={() => void start(state.file)}>
              Réessayer
            </Button>
          )}
          <Button
            size="sm"
            variant={document.status === 'received' ? 'secondary' : 'primary'}
            loading={busy}
            onClick={() => input.current?.click()}
          >
            {document.status === 'received' ? 'Remplacer' : 'Déposer'}
          </Button>
          {document.status === 'received' && !busy && (
            <Button size="sm" variant="ghost" onClick={onRemove}>
              Retirer
            </Button>
          )}
        </div>
      )}
    </li>
  )
}
