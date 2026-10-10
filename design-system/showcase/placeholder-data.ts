// Fictional placeholder content for the showcase only. Portals must use the
// canonical HC-005 demo fixtures instead; nothing here is real or reusable data.

import type { Tone } from '../src'

export interface PlaceholderRequest {
  reference: string
  kind: string
  requester: string
  submitted: string
  status: { label: string; tone: Tone }
}

export const placeholderRequests: readonly PlaceholderRequest[] = [
  {
    reference: 'SR-0101',
    kind: 'Synchronization',
    requester: 'Hospital A → Hospital B',
    submitted: '08 Oct 2026',
    status: { label: 'Pending review', tone: 'warning' },
  },
  {
    reference: 'RR-0042',
    kind: 'Research access',
    requester: 'Research Project Alpha',
    submitted: '06 Oct 2026',
    status: { label: 'Approved', tone: 'success' },
  },
  {
    reference: 'HO-0007',
    kind: 'Hospital onboarding',
    requester: 'Hospital C',
    submitted: '02 Oct 2026',
    status: { label: 'Rejected', tone: 'danger' },
  },
  {
    reference: 'HO-0008',
    kind: 'Hospital onboarding',
    requester: 'Hospital D',
    submitted: '01 Oct 2026',
    status: { label: 'Draft', tone: 'neutral' },
  },
]
