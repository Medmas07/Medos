import { describe, expect, it } from 'vitest'
import { DEMO_MANAGER_ID, DEMO_ORGANIZATION_ID, loadOnboardingSnapshot, scenarioFromSearch } from '../src/services/onboardingService'
import {
  applyRemoval,
  applyUpload,
  canRemove,
  canUpload,
  documentChecklist,
  formatSize,
  MAX_FILE_BYTES,
  uploadDocument,
  validateFile,
} from '../src/services/documentService'
import { applyRegistration, demoRegistrationInput, submitRegistration } from '../src/services/registrationService'
import type { OnboardingSnapshot } from '../src/types/onboarding'

const now = new Date('2026-10-10T11:00:00+01:00')
const pdf = (name = 'attestation-fictive.pdf', size = 120_000) => ({ name, size, type: 'application/pdf' })
const upload = (file = pdf(), simulateFailure = false) => uploadDocument(file, { stepMs: 0, now, simulateFailure })

const load = (scenario: 'nominal' | 'empty' = 'nominal') =>
  loadOnboardingSnapshot(DEMO_ORGANIZATION_ID, DEMO_MANAGER_ID, { scenario, delayMs: 0 })

async function registeredDraft() {
  const result = await submitRegistration(demoRegistrationInput(), { delayMs: 0, now })
  if (result.kind !== 'accepted') throw new Error('expected acceptance')
  return applyRegistration(await load('empty'), demoRegistrationInput(), result.receipt)
}

const step = (snapshot: OnboardingSnapshot) => snapshot.steps.find((s) => s.id === 'documents')!

describe('Hospital document upload (MOCKED)', () => {
  it('lists the three required documents of the Cap Azur fixture, insurance missing', async () => {
    const { application } = await load()
    const checklist = documentChecklist(application!)
    expect(checklist.map((d) => [d.type, d.status])).toEqual([
      ['statutes', 'received'],
      ['operating_license', 'received'],
      ['insurance_certificate', 'missing'],
    ])
  })

  it('under review, accepts only the missing piece, and never a removal', async () => {
    const { application } = await load()
    const [statutes, , insurance] = documentChecklist(application!)
    expect(canUpload(application!, insurance)).toBe(true)
    expect(canUpload(application!, statutes)).toBe(false)
    expect(canRemove(application!, statutes)).toBe(false)
  })

  it('completes the documents step when the missing certificate is provided under review', async () => {
    const snapshot = await load()
    expect(step(snapshot)).toMatchObject({ status: 'attention', detail: '1 document à fournir.' })

    const next = applyUpload(snapshot, 'insurance_certificate', await upload())
    const insurance = next.application!.documents.find((d) => d.type === 'insurance_certificate')!
    expect(insurance).toMatchObject({ status: 'received', title: 'attestation-fictive.pdf' })
    expect(insurance.upload).toEqual({
      fileName: 'attestation-fictive.pdf',
      sizeBytes: 120_000,
      mediaType: 'application/pdf',
      uploadedAt: now.toISOString(),
    })
    expect(next.application!.status).toBe('human_review')
    expect(step(next).status).toBe('completed')
    expect(() => applyUpload(next, 'statutes', insurance.upload!)).toThrow('ne peut plus')
  })

  it('lets a draft deposit, replace, and remove documents, tracking progress', async () => {
    let snapshot = await registeredDraft()
    expect(documentChecklist(snapshot.application!).every((d) => d.status === 'missing')).toBe(true)
    expect(step(snapshot).status).toBe('pending')

    snapshot = applyUpload(snapshot, 'statutes', await upload(pdf('statuts.pdf')))
    expect(step(snapshot)).toMatchObject({ status: 'in_progress', detail: '1 / 3 documents déposés.' })

    snapshot = applyUpload(snapshot, 'statutes', await upload(pdf('statuts-v2.pdf')))
    expect(snapshot.application!.documents.find((d) => d.type === 'statutes')?.upload?.fileName).toBe('statuts-v2.pdf')

    snapshot = applyUpload(snapshot, 'operating_license', await upload({ name: 'autorisation.png', size: 900, type: 'image/png' }))
    snapshot = applyUpload(snapshot, 'insurance_certificate', await upload())
    expect(step(snapshot).status).toBe('completed')

    snapshot = applyRemoval(snapshot, 'statutes')
    const statutes = snapshot.application!.documents.find((d) => d.type === 'statutes')!
    expect(statutes).toEqual({ id: 'doc-local-statutes', type: 'statutes', title: "Statuts de l'établissement", status: 'missing' })
    expect(step(snapshot).detail).toBe('2 / 3 documents déposés.')
    expect(snapshot.steps.find((s) => s.id === 'decision')?.status).toBe('pending')
  })

  it('rejects unsupported, empty, mismatched, and oversized files', () => {
    expect(validateFile(pdf())).toBeNull()
    expect(validateFile({ name: 'scan.JPG', size: 10, type: 'image/jpeg' })).toBeNull()
    expect(validateFile({ name: 'notes.docx', size: 10, type: 'application/msword' })).toContain('Format')
    expect(validateFile({ name: 'faux.pdf', size: 10, type: 'image/png' })).toContain('Format')
    expect(validateFile(pdf('vide.pdf', 0))).toContain('vide')
    expect(validateFile(pdf('gros.pdf', MAX_FILE_BYTES + 1))).toContain('10 Mo')
  })

  it('reports simulated progress, then fails at 60 % in the failure scenario', async () => {
    const seen: number[] = []
    await uploadDocument(pdf(), { stepMs: 0, onProgress: (p) => seen.push(p) })
    expect(seen).toEqual([20, 40, 60, 80, 100])

    const partial: number[] = []
    await expect(
      uploadDocument(pdf(), { stepMs: 0, simulateFailure: true, onProgress: (p) => partial.push(p) }),
    ).rejects.toThrow('interrompu')
    expect(partial).toEqual([20, 40])
    await expect(upload({ name: 'x.exe', size: 5, type: 'application/octet-stream' })).rejects.toThrow('Format')
    expect(scenarioFromSearch('?demo=echec-document')).toBe('document-failure')
  })

  it('formats file sizes in French units', () => {
    expect(formatSize(900)).toBe('900 o')
    expect(formatSize(120_000)).toBe('117 Ko')
    expect(formatSize(2_621_440)).toBe('2,5 Mo')
  })
})
