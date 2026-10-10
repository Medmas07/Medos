import type {
  ApplicationDocument,
  DocumentType,
  DocumentUpload,
  HospitalApplication,
  OnboardingSnapshot,
} from '../types/onboarding'
import { deriveSteps } from './onboardingService'

/**
 * MOCKED administrative document upload (HC-053). The portal never reads or
 * sends file content: only the file name, size, and media type are kept, in
 * memory. Upload progress is simulated. A document-metadata contract is PLANNED.
 */

export interface RequiredDocument {
  type: DocumentType
  label: string
  hint: string
}

export const REQUIRED_DOCUMENTS: readonly RequiredDocument[] = [
  { type: 'statutes', label: "Statuts de l'établissement", hint: 'Statuts en vigueur, signés.' },
  { type: 'operating_license', label: "Autorisation d'exercice", hint: "Autorisation délivrée par l'autorité de tutelle." },
  { type: 'insurance_certificate', label: "Attestation d'assurance", hint: "Responsabilité civile de l'établissement, en cours de validité." },
]

export const MAX_FILE_BYTES = 10 * 1024 * 1024
const ACCEPTED: Record<string, readonly string[]> = {
  'application/pdf': ['pdf'],
  'image/jpeg': ['jpg', 'jpeg'],
  'image/png': ['png'],
}
/** Value for the file input's `accept` attribute. */
export const ACCEPT_ATTRIBUTE = Object.entries(ACCEPTED)
  .flatMap(([type, extensions]) => [type, ...extensions.map((e) => `.${e}`)])
  .join(',')

/** One entry per required document, from the application's documents or marked missing. Pure. */
export function documentChecklist(application: HospitalApplication): ApplicationDocument[] {
  return REQUIRED_DOCUMENTS.map(
    (required) =>
      application.documents.find((d) => d.type === required.type) ?? {
        id: `doc-local-${required.type}`,
        type: required.type,
        title: required.label,
        status: 'missing',
      },
  )
}

/**
 * A draft accepts any change. An application under review only accepts the
 * pieces still missing or rejected. A decided application accepts nothing.
 */
export function canUpload(application: HospitalApplication, document: ApplicationDocument): boolean {
  if (application.status === 'draft') return true
  if (application.status === 'pending' || application.status === 'human_review') return document.status !== 'received'
  return false
}

/** Removing a deposited file is only possible on a draft. */
export function canRemove(application: HospitalApplication, document: ApplicationDocument): boolean {
  return application.status === 'draft' && document.status === 'received'
}

export interface FileDescription {
  name: string
  size: number
  type: string
}

/** Returns an error message, or `null` when the file is acceptable. Pure. */
export function validateFile(file: FileDescription): string | null {
  const extension = file.name.split('.').pop()?.toLowerCase() ?? ''
  const extensions = ACCEPTED[file.type]
  if (!extensions || !extensions.includes(extension)) return 'Format non accepté : PDF, JPEG ou PNG uniquement.'
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
export async function uploadDocument(
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

function withDocuments(snapshot: OnboardingSnapshot, documents: ApplicationDocument[]): OnboardingSnapshot {
  const application = { ...snapshot.application!, documents }
  return { ...snapshot, application, steps: deriveSteps(snapshot.organization, application) }
}

/** Returns the snapshot with the document received from this upload. Pure. */
export function applyUpload(snapshot: OnboardingSnapshot, type: DocumentType, upload: DocumentUpload): OnboardingSnapshot {
  const application = snapshot.application
  if (!application) throw new Error('Aucune candidature : inscrivez d’abord l’établissement.')
  const current = documentChecklist(application).find((d) => d.type === type)!
  if (!canUpload(application, current)) throw new Error('Ce document ne peut plus être modifié.')
  return withDocuments(
    snapshot,
    documentChecklist(application).map((d) =>
      d.type === type ? { ...d, title: upload.fileName, status: 'received' as const, upload } : d,
    ),
  )
}

/** Returns the snapshot with the document of this type missing again (draft only). Pure. */
export function applyRemoval(snapshot: OnboardingSnapshot, type: DocumentType): OnboardingSnapshot {
  const application = snapshot.application
  const current = application && documentChecklist(application).find((d) => d.type === type)
  if (!application || !current || !canRemove(application, current)) {
    throw new Error('Ce document ne peut pas être retiré.')
  }
  const label = REQUIRED_DOCUMENTS.find((r) => r.type === type)!.label
  return withDocuments(
    snapshot,
    documentChecklist(application).map((d) =>
      d.type === type ? { id: d.id, type, title: label, status: 'missing' as const } : d,
    ),
  )
}
