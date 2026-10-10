import type {
  DocumentUpload,
  ProjectDocumentRef,
  ProjectDocumentType,
  ResearchProject,
  ResearchSnapshot,
} from '../types/research'
import { editableDraft, withProject } from './projectCreation'

/**
 * Research protocol and document upload (HC-093), MOCKED. The portal never
 * reads or sends file content: only the file name, size, and media type are
 * kept, in the portal's session state. Upload progress is simulated. No
 * Research Service is called; a document-metadata contract is PLANNED.
 */

export interface ProjectDocumentDefinition {
  type: ProjectDocumentType
  label: string
  hint: string
  required: boolean
}

/** The protocol is required before the access request (HC-097); the others are optional. */
export const PROJECT_DOCUMENTS: readonly ProjectDocumentDefinition[] = [
  {
    type: 'protocol',
    label: 'Protocole de recherche',
    hint: 'Objectifs, méthode, population, variables et analyses prévues.',
    required: true,
  },
  {
    type: 'data_management_plan',
    label: 'Plan de gestion des données',
    hint: 'Traitements prévus, durée de conservation des résultats, mesures de confidentialité.',
    required: false,
  },
  {
    type: 'information_notice',
    label: "Note d'information des patients",
    hint: "Information des personnes dont les données sont analysées, si le protocole l'exige.",
    required: false,
  },
]

export const MAX_FILE_BYTES = 10 * 1024 * 1024
/** Value for the file input's `accept` attribute. */
export const ACCEPT_ATTRIBUTE = 'application/pdf,.pdf'

export interface ProjectDocument {
  type: ProjectDocumentType
  status: 'received' | 'missing'
  /** Set when received. */
  document: ProjectDocumentRef | null
}

/** One entry per expected document, from the project or marked missing. Pure. */
export function documentChecklist(project: ResearchProject): ProjectDocument[] {
  return PROJECT_DOCUMENTS.map(({ type }) => {
    const document =
      type === 'protocol'
        ? project.protocolDocument
        : (project.supportingDocuments?.find((d) => d.type === type) ?? null)
    return { type, status: document ? 'received' : 'missing', document }
  })
}

export interface FileDescription {
  name: string
  size: number
  type: string
}

/** Returns an error message, or `null` when the file is acceptable. Pure. */
export function validateFile(file: FileDescription): string | null {
  const extension = file.name.split('.').pop()?.toLowerCase() ?? ''
  if (file.type !== 'application/pdf' || extension !== 'pdf') return 'Format non accepté : PDF uniquement.'
  if (file.size === 0) return 'Le fichier est vide.'
  if (file.size > MAX_FILE_BYTES) return 'Le fichier dépasse 10 Mo.'
  return null
}

export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} Ko`
  return `${(bytes / (1024 * 1024)).toFixed(1).replace('.', ',')} Mo`
}

export interface UploadOptions {
  /** Called with 20, 40, 60, 80, 100. */
  onProgress?: (percent: number) => void
  /** Simulates an interrupted transfer at 60 % (demo scenario). */
  simulateFailure?: boolean
  stepMs?: number
  now?: Date
}

/** Simulated upload of a validated file: only its metadata is returned. */
export async function uploadProjectDocument(
  file: FileDescription,
  { onProgress, simulateFailure = false, stepMs = 150, now = new Date() }: UploadOptions = {},
): Promise<DocumentUpload> {
  const error = validateFile(file)
  if (error) throw new Error(error)
  for (let percent = 20; percent <= 100; percent += 20) {
    await new Promise((resolve) => setTimeout(resolve, stepMs))
    if (simulateFailure && percent === 60) {
      throw new Error('Le transfert simulé a été interrompu (scénario de démonstration).')
    }
    onProgress?.(percent)
  }
  return { fileName: file.name, sizeBytes: file.size, mediaType: file.type, uploadedAt: now.toISOString() }
}

function setDocument(
  project: ResearchProject,
  type: ProjectDocumentType,
  document: ProjectDocumentRef | null,
): ResearchProject {
  if (type === 'protocol') return { ...project, protocolDocument: document }
  const others = (project.supportingDocuments ?? []).filter((d) => d.type !== type)
  return { ...project, supportingDocuments: document ? [...others, document] : others }
}

/** Returns the snapshot with this upload as the project's document of this type. Pure. */
export function applyDocumentUpload(
  snapshot: ResearchSnapshot,
  projectId: string,
  type: ProjectDocumentType,
  upload: DocumentUpload,
): ResearchSnapshot {
  const { project } = editableDraft(snapshot, projectId)
  const document: ProjectDocumentRef = {
    // Follows the fixture identifiers (`doc-proj-001-protocole`).
    id: `doc-${project.id}-${type === 'protocol' ? 'protocole' : type.replaceAll('_', '-')}`,
    title: upload.fileName,
    ...(type !== 'protocol' && { type }),
    upload,
  }
  return withProject(snapshot, setDocument(project, type, document))
}

/** Returns the snapshot with the project's document of this type missing again. Pure. */
export function applyDocumentRemoval(
  snapshot: ResearchSnapshot,
  projectId: string,
  type: ProjectDocumentType,
): ResearchSnapshot {
  const { project } = editableDraft(snapshot, projectId)
  return withProject(snapshot, setDocument(project, type, null))
}
