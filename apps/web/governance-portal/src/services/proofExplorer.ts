/**
 * Blockchain proof explorer (HC-080, D1). MOCKED BLOCKCHAIN.
 *
 * The "ledger" is the simulated proof list in demo-data/governance.json: no chain, no
 * network, no consensus, no real anchoring. What this module does for real is check each
 * proof in the browser: recompute its SHA-256 from the anchored payload, confirm it is
 * linked to the audit event it claims, and confirm the payload holds only minimized
 * governance fields, never medical data. The AuditLedgerPort and a simulated or real
 * ledger are PLANNED (HC-190 to HC-194).
 */
import type { GovernanceAuditEvent, LedgerProof } from '../types/governance'

/** The only fields a proof may anchor; same set as demo-data/check_fixtures.py. */
export const ALLOWED_PROOF_FIELDS: readonly string[] = [
  'eventId',
  'decisionId',
  'outcome',
  'decidedAt',
  'organizationIds',
  'version',
]

/**
 * Canonical JSON identical to Python's json.dumps(payload, sort_keys=True,
 * separators=(',', ':')), which check_fixtures.py hashes: keys sorted at every depth,
 * no whitespace, and non-ASCII characters escaped as \\uXXXX (ensure_ascii).
 */
export function canonicalJson(value: unknown): string {
  const sortKeys = (v: unknown): unknown => {
    if (Array.isArray(v)) return v.map(sortKeys)
    if (v !== null && typeof v === 'object') {
      return Object.fromEntries(
        Object.keys(v as Record<string, unknown>)
          .sort()
          .map((key) => [key, sortKeys((v as Record<string, unknown>)[key])]),
      )
    }
    return v
  }
  return JSON.stringify(sortKeys(value)).replace(
    // Python escapes everything outside printable ASCII (space to tilde), DEL included.
    /[\u007f-\uffff]/g,
    (c) => `\\u${c.charCodeAt(0).toString(16).padStart(4, '0')}`,
  )
}

export async function sha256Hex(text: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text))
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, '0')).join('')
}

/**
 * - verified: the recomputed hash matches and the proof is consistent.
 * - tampered: the recomputed hash differs from the recorded one.
 * - inconsistent: the hash matches, but the proof points to the wrong event or anchors
 *   fields that are not allowed.
 */
export type ProofState = 'verified' | 'tampered' | 'inconsistent'

export interface ProofVerification {
  proof: LedgerProof
  state: ProofState
  recomputedHash: string
  hashMatches: boolean
  /** The payload's eventId is the proof's audit event, and that event exists. */
  eventLinked: boolean
  /** Anchored fields outside ALLOWED_PROOF_FIELDS; empty when minimized. */
  forbiddenFields: string[]
  /** The fixture's own verificationStatus disagrees with the recomputation. */
  claimDisagrees: boolean
}

export async function verifyProof(
  proof: LedgerProof,
  eventFor: (id: string) => GovernanceAuditEvent | undefined,
): Promise<ProofVerification> {
  const recomputedHash = await sha256Hex(canonicalJson(proof.anchoredPayload))
  const hashMatches = recomputedHash === proof.hash
  const eventLinked = proof.anchoredPayload.eventId === proof.auditEventId && Boolean(eventFor(proof.auditEventId))
  const forbiddenFields = Object.keys(proof.anchoredPayload).filter((k) => !ALLOWED_PROOF_FIELDS.includes(k))
  const state: ProofState = !hashMatches
    ? 'tampered'
    : !eventLinked || forbiddenFields.length > 0
      ? 'inconsistent'
      : 'verified'
  return {
    proof,
    state,
    recomputedHash,
    hashMatches,
    eventLinked,
    forbiddenFields,
    claimDisagrees: (proof.verificationStatus === 'verified') !== (state === 'verified'),
  }
}

export function verifyProofs(
  proofs: readonly LedgerProof[],
  eventFor: (id: string) => GovernanceAuditEvent | undefined,
): Promise<ProofVerification[]> {
  return Promise.all(proofs.map((proof) => verifyProof(proof, eventFor)))
}

export function countByState(results: readonly ProofVerification[]): Record<ProofState, number> {
  const counts: Record<ProofState, number> = { verified: 0, tampered: 0, inconsistent: 0 }
  for (const r of results) counts[r.state] += 1
  return counts
}

export const PROOF_STATE_LABELS: Record<ProofState, string> = {
  verified: 'Vérifiée',
  tampered: 'Altérée',
  inconsistent: 'Incohérente',
}
