import { useEffect, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  DemoBadge,
  PageHeader,
} from '@hackcure/design-system'
import { governanceService } from '../../services/governanceService'

interface VerifierViewProps {
  initialProofId?: string
}

export function VerifierView({ initialProofId = 'proof-003' }: VerifierViewProps) {
  const proofs = governanceService.getLedgerProofs()
  const [selectedProofId, setSelectedProofId] = useState<string>(initialProofId)
  const [tamperedPayloadText, setTamperedPayloadText] = useState<string>(() => {
    const p = proofs.find((item) => item.id === initialProofId) ?? proofs[0]
    return p ? JSON.stringify(p.anchoredPayload, null, 2) : ''
  })
  const [computedHash, setComputedHash] = useState<string>('')
  const [isVerifying, setIsVerifying] = useState<boolean>(false)

  const selectedProof = proofs.find((p) => p.id === selectedProofId) ?? proofs[0]

  const handleSelectProof = (proofId: string) => {
    setSelectedProofId(proofId)
    const p = proofs.find((item) => item.id === proofId)
    if (p) {
      setTamperedPayloadText(JSON.stringify(p.anchoredPayload, null, 2))
    }
  }

  useEffect(() => {
    async function calculate() {
      if (!tamperedPayloadText) return
      setIsVerifying(true)
      try {
        const parsed = JSON.parse(tamperedPayloadText)
        // Compute canonical string sorted by keys matching check_fixtures.py
        const canonicalStr = JSON.stringify(parsed, Object.keys(parsed).sort())
        const hash = await governanceService.computeSha256(canonicalStr)
        setComputedHash(hash)
      } catch {
        setComputedHash('Erreur : JSON invalide')
      } finally {
        setIsVerifying(false)
      }
    }
    void calculate()
  }, [tamperedPayloadText])

  const isValidMatch = selectedProof && computedHash === selectedProof.hash

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Cryptographie & Confiance Numérique"
        title="Inspecteur et Vérificateur de Preuves d'Ancrage"
        description="Vérification mathématique indépendante côté client des empreintes SHA-256 enregistrées sur le registre de gouvernance."
      />

      <Alert tone="info" title="Vérification à divulgation nulle de secret">
        Le vérificateur recalcule dynamiquement le condensat SHA-256 à partir du payload canonique minimisé sans nécessiter d'accès à des données médicales.
      </Alert>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Left: Proof selector and details */}
        <div className="lg:col-span-5 space-y-4">
          <Card title="Sélection de la Preuve à Auditer">
            <div className="space-y-2">
              {proofs.map((p) => (
                <div
                  key={p.id}
                  onClick={() => handleSelectProof(p.id)}
                  className={`cursor-pointer rounded-md border p-3 text-xs transition-colors ${selectedProofId === p.id
                    ? 'border-brand-600 bg-brand-50'
                    : 'border-slate-200 bg-white hover:bg-slate-50'
                    }`}
                >
                  <div className="flex items-center justify-between font-semibold text-slate-900">
                    <span>{p.id} ({p.anchoredPayload.decisionId})</span>
                    <DemoBadge>Simulé</DemoBadge>
                  </div>
                  <div className="mt-1 text-slate-500">Événement : {p.auditEventId}</div>
                  <div className="mt-1 truncate font-mono text-[11px] text-slate-600">{p.hash}</div>
                </div>
              ))}
            </div>
          </Card>

          <Card title="Statut de l'Ancrage au Registre">
            <dl className="space-y-2 text-xs">
              <div className="flex justify-between border-b border-slate-100 pb-1.5">
                <dt className="text-slate-500">Registre cible :</dt>
                <dd className="font-semibold text-slate-800">{selectedProof?.ledger}</dd>
              </div>
              <div className="flex justify-between border-b border-slate-100 pb-1.5">
                <dt className="text-slate-500">Algorithme :</dt>
                <dd className="font-mono text-slate-800">{selectedProof?.hashAlgorithm}</dd>
              </div>
              <div className="flex justify-between border-b border-slate-100 pb-1.5">
                <dt className="text-slate-500">Date d'ancrage :</dt>
                <dd className="text-slate-800">
                  {selectedProof && new Date(selectedProof.anchoredAt).toLocaleString('fr-TN')}
                </dd>
              </div>
              <div className="flex justify-between pt-1">
                <dt className="text-slate-500">Empreinte enregistrée :</dt>
                <dd className="max-w-[200px] truncate font-mono text-slate-700" title={selectedProof?.hash}>
                  {selectedProof?.hash}
                </dd>
              </div>
            </dl>
          </Card>
        </div>

        {/* Right: Interactive hash computation and tamper testing */}
        <div className="lg:col-span-7 space-y-4">
          <Card
            title="Inspecteur Cryptographique Interactif"
            actions={
              <Button
                size="sm"
                variant="secondary"
                onClick={() => {
                  if (selectedProof) {
                    setTamperedPayloadText(JSON.stringify(selectedProof.anchoredPayload, null, 2))
                  }
                }}
              >
                Réinitialiser le Payload
              </Button>
            }
          >
            <p className="mb-2 text-xs text-slate-600">
              Vous pouvez tester la robustesse de l'audit en modifiant un champ ci-dessous (par exemple remplacer <code>"approved"</code> par <code>"rejected"</code>) pour observer la détection instantanée d'altération :
            </p>

            <textarea
              className="w-full rounded-md border border-slate-300 p-2.5 font-mono text-xs text-slate-800 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              rows={8}
              value={tamperedPayloadText}
              onChange={(e) => setTamperedPayloadText(e.target.value)}
            />

            <div className="mt-4 space-y-3 rounded-md bg-slate-50 p-4">
              <div>
                <span className="text-xs font-semibold text-slate-600">Condensat SHA-256 Recalculé côté client :</span>
                <div className="mt-1 break-all rounded bg-white p-2 font-mono text-xs text-slate-900 border border-slate-200">
                  {isVerifying ? 'Calcul en cours...' : computedHash}
                </div>
              </div>

              <div>
                <span className="text-xs font-semibold text-slate-600">Empreinte Officielle du Registre :</span>
                <div className="mt-1 break-all rounded bg-white p-2 font-mono text-xs text-slate-700 border border-slate-200">
                  {selectedProof?.hash}
                </div>
              </div>

              <div className="pt-2">
                {isValidMatch ? (
                  <div className="flex items-center gap-2 rounded-md bg-success-50 p-3 text-xs text-success-800 border border-success-200">
                    <Badge tone="success" dot>Preuve Intègre</Badge>
                    <span>L'empreinte recalculée concorde rigoureusement avec le registre. La décision n'a subi aucune modification.</span>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 rounded-md bg-danger-50 p-3 text-xs text-danger-800 border border-danger-200">
                    <Badge tone="danger" dot>Divergence / Altération</Badge>
                    <span>Le condensat ne correspond pas au registre d'audit. Toute tentative de modification est immédiatement invalidée.</span>
                  </div>
                )}
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
