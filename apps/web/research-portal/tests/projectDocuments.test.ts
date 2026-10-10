import { describe, expect, it } from 'vitest'
import { createResearchProject } from '../src/services/projectCreation'
import {
  applyDocumentRemoval,
  applyDocumentUpload,
  canEditDocuments,
  defaultProjectId,
  documentChecklist,
  uploadProjectDocument,
  validateFile,
} from '../src/services/projectDocuments'
import { DEMO_RESEARCHER_ID, loadResearchSnapshot, scenarioFromSearch } from '../src/services/researchService'
import type { DocumentUpload, ResearchSnapshot } from '../src/types/research'

const NOW = new Date('2026-10-10T12:00:00+01:00')

const PDF = { name: 'Protocole_IRC_v1.pdf', size: 245_000, type: 'application/pdf' }

const UPLOAD: DocumentUpload = {
  fileName: PDF.name,
  sizeBytes: PDF.size,
  mediaType: PDF.type,
  uploadedAt: NOW.toISOString(),
}

/** The nominal snapshot with a new draft, `proj-003`, first. */
async function withDraft(): Promise<ResearchSnapshot> {
  const snapshot = await loadResearchSnapshot(DEMO_RESEARCHER_ID, { delayMs: 0, now: NOW })
  const created = await createResearchProject(
    snapshot,
    {
      title: 'Insuffisance rénale chronique et diabète',
      summary: "Décrire la fréquence de l'insuffisance rénale chronique chez les adultes diabétiques suivis.",
    },
    { delayMs: 0, now: NOW },
  )
  return created.snapshot
}

const projectOf = (snapshot: ResearchSnapshot, id: string) => snapshot.projects.find((s) => s.project.id === id)!

describe('Research protocol and document upload (HC-093, MOCKED)', () => {
  it('lists the required protocol and the optional documents, reading fixture protocols as received', async () => {
    const snapshot = await withDraft()
    expect(documentChecklist(projectOf(snapshot, 'proj-003').project).map((d) => [d.type, d.status])).toEqual([
      ['protocol', 'missing'],
      ['data_management_plan', 'missing'],
      ['information_notice', 'missing'],
    ])
    const [protocol] = documentChecklist(projectOf(snapshot, 'proj-001').project)
    expect(protocol).toMatchObject({ status: 'received', document: { title: 'Protocole_v2.pdf' } })
  })

  it('allows changes only on a draft whose access request is not submitted', async () => {
    const snapshot = await withDraft()
    expect(canEditDocuments(projectOf(snapshot, 'proj-003'))).toBe(true)
    expect(canEditDocuments(projectOf(snapshot, 'proj-001'))).toBe(false)
    expect(canEditDocuments(projectOf(snapshot, 'proj-002'))).toBe(false)
    expect(() => applyDocumentUpload(snapshot, 'proj-002', 'protocol', UPLOAD)).toThrow('ne peuvent plus être modifiés')
    expect(() => applyDocumentRemoval(snapshot, 'proj-001', 'protocol')).toThrow('ne peuvent plus être modifiés')
    expect(() => applyDocumentUpload(snapshot, 'proj-999', 'protocol', UPLOAD)).toThrow('Projet inconnu')
  })

  it('opens the newest editable draft first', async () => {
    expect(defaultProjectId(await withDraft())).toBe('proj-003')
    const nominal = await loadResearchSnapshot(DEMO_RESEARCHER_ID, { delayMs: 0, now: NOW })
    expect(defaultProjectId(nominal)).toBe('proj-002')
    const empty = await loadResearchSnapshot(DEMO_RESEARCHER_ID, { scenario: 'empty', delayMs: 0, now: NOW })
    expect(defaultProjectId(empty)).toBeNull()
  })

  it('accepts only non-empty PDF files of at most 10 MB', () => {
    expect(validateFile(PDF)).toBeNull()
    expect(validateFile({ ...PDF, name: 'protocole.docx', type: 'application/msword' })).toContain('PDF uniquement')
    expect(validateFile({ ...PDF, name: 'protocole.png' })).toContain('PDF uniquement')
    expect(validateFile({ ...PDF, size: 0 })).toBe('Le fichier est vide.')
    expect(validateFile({ ...PDF, size: 10 * 1024 * 1024 + 1 })).toBe('Le fichier dépasse 10 Mo.')
  })

  it('simulates progress and returns only file metadata', async () => {
    const progress: number[] = []
    const upload = await uploadProjectDocument(PDF, { stepMs: 0, now: NOW, onProgress: (p) => progress.push(p) })
    expect(progress).toEqual([20, 40, 60, 80, 100])
    expect(upload).toEqual(UPLOAD)
  })

  it('refuses an invalid file and can simulate an interrupted transfer', async () => {
    await expect(uploadProjectDocument({ ...PDF, size: 0 }, { stepMs: 0 })).rejects.toThrow('vide')
    const progress: number[] = []
    await expect(
      uploadProjectDocument(PDF, { stepMs: 0, simulateFailure: true, onProgress: (p) => progress.push(p) }),
    ).rejects.toThrow('interrompu')
    expect(progress).toEqual([20, 40])
    expect(scenarioFromSearch('?demo=echec-depot')).toBe('upload-failure')
  })

  it('records the protocol on the draft and updates the page summary, leaving the snapshot untouched', async () => {
    const snapshot = await withDraft()
    const next = applyDocumentUpload(snapshot, 'proj-003', 'protocol', UPLOAD)

    expect(projectOf(next, 'proj-003').project.protocolDocument).toEqual({
      id: 'doc-proj-003-protocole',
      title: PDF.name,
      upload: UPLOAD,
    })
    expect(next.pages.find((p) => p.id === 'protocol')?.detail).toBe('3 protocoles déposé(s).')
    expect(projectOf(snapshot, 'proj-003').project.protocolDocument).toBeNull()
    // A document requests no data access.
    expect(projectOf(next, 'proj-003')).toMatchObject({ request: null, authorized: false })
    for (const id of ['workspace', 'execution', 'results']) {
      expect(next.pages.find((p) => p.id === id)?.status).toBe(snapshot.pages.find((p) => p.id === id)?.status)
    }
  })

  it('replaces and removes supporting documents independently of the protocol', async () => {
    let snapshot = await withDraft()
    snapshot = applyDocumentUpload(snapshot, 'proj-003', 'protocol', UPLOAD)
    snapshot = applyDocumentUpload(snapshot, 'proj-003', 'data_management_plan', { ...UPLOAD, fileName: 'PGD_v1.pdf' })
    snapshot = applyDocumentUpload(snapshot, 'proj-003', 'data_management_plan', { ...UPLOAD, fileName: 'PGD_v2.pdf' })

    expect(projectOf(snapshot, 'proj-003').project.supportingDocuments).toEqual([
      { id: 'doc-proj-003-data-management-plan', title: 'PGD_v2.pdf', type: 'data_management_plan', upload: { ...UPLOAD, fileName: 'PGD_v2.pdf' } },
    ])

    snapshot = applyDocumentRemoval(snapshot, 'proj-003', 'data_management_plan')
    expect(projectOf(snapshot, 'proj-003').project.supportingDocuments).toEqual([])
    expect(projectOf(snapshot, 'proj-003').project.protocolDocument?.title).toBe(PDF.name)

    snapshot = applyDocumentRemoval(snapshot, 'proj-003', 'protocol')
    expect(documentChecklist(projectOf(snapshot, 'proj-003').project)[0].status).toBe('missing')
  })
})
