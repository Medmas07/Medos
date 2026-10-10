import { describe, expect, it } from 'vitest'
import { governanceService } from '../src/services/governanceService'
import {
  canonicalJson,
  countByState,
  sha256Hex,
  verifyProof,
  verifyProofs,
} from '../src/services/proofExplorer'
import type { LedgerProof } from '../src/types/governance'

const eventFor = (id: string) => governanceService.getAuditEvents().find((e) => e.id === id)
const proof = (id: string) => governanceService.getLedgerProofs().find((p) => p.id === id)!

/** A copy of proof-003 with a changed payload, re-hashed so only the other checks can fail. */
async function rehashed(changes: Record<string, unknown>): Promise<LedgerProof> {
  const original = proof('proof-003')
  const anchoredPayload = { ...original.anchoredPayload, ...changes } as LedgerProof['anchoredPayload']
  return { ...original, anchoredPayload, hash: await sha256Hex(canonicalJson(anchoredPayload)) }
}

describe('Canonical JSON (HC-080)', () => {
  it('matches Python json.dumps(sort_keys=True, separators=(",", ":")) byte for byte', () => {
    // Reference produced by Python 3 for the same value.
    const value = { b: 'é😀\u007f', a: { z: 1, y: [{ d: 2, c: 3 }] } }

    expect(canonicalJson(value)).toBe('{"a":{"y":[{"c":3,"d":2}],"z":1},"b":"\\u00e9\\ud83d\\ude00\\u007f"}')
  })

  it('keeps nested keys, so a change inside a nested object changes the hash', async () => {
    const a = await sha256Hex(canonicalJson({ meta: { outcome: 'approved' } }))
    const b = await sha256Hex(canonicalJson({ meta: { outcome: 'rejected' } }))

    expect(canonicalJson({ meta: { outcome: 'approved' } })).toBe('{"meta":{"outcome":"approved"}}')
    expect(a).not.toBe(b)
  })
})

describe('Proof verification (HC-080)', () => {
  it('verifies both demo proofs by recomputing their hashes', async () => {
    const results = await verifyProofs(governanceService.getLedgerProofs(), eventFor)

    expect(results.map((r) => [r.proof.id, r.state])).toEqual([
      ['proof-003', 'verified'],
      ['proof-004', 'verified'],
    ])
    for (const r of results) {
      expect(r.recomputedHash).toBe(r.proof.hash)
      expect(r).toMatchObject({ hashMatches: true, eventLinked: true, forbiddenFields: [], claimDisagrees: false })
    }
  })

  it('detects a tampered decision even though the proof still claims to be verified', async () => {
    const original = proof('proof-003')
    const tampered = { ...original, anchoredPayload: { ...original.anchoredPayload, outcome: 'rejected' } }

    const result = await verifyProof(tampered, eventFor)

    expect(result).toMatchObject({ state: 'tampered', hashMatches: false, claimDisagrees: true })
  })

  it('flags a proof that anchors medical data, even with a matching hash', async () => {
    const result = await verifyProof(await rehashed({ diagnosis: 'Asthme' }), eventFor)

    expect(result).toMatchObject({ state: 'inconsistent', hashMatches: true, forbiddenFields: ['diagnosis'] })
  })

  it('flags a proof that points to another event, or to a missing one', async () => {
    const wrongEvent = await verifyProof(await rehashed({ eventId: 'evt-004' }), eventFor)
    const missingEvent = await verifyProof(proof('proof-003'), () => undefined)

    expect(wrongEvent).toMatchObject({ state: 'inconsistent', eventLinked: false })
    expect(missingEvent).toMatchObject({ state: 'inconsistent', eventLinked: false })
  })

  it('counts proofs by state', async () => {
    const results = [
      await verifyProof(proof('proof-003'), eventFor),
      await verifyProof(await rehashed({ diagnosis: 'x' }), eventFor),
      await verifyProof({ ...proof('proof-004'), hash: '0'.repeat(64) }, eventFor),
    ]

    expect(countByState(results)).toEqual({ verified: 1, tampered: 1, inconsistent: 1 })
  })
})
