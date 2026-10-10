import type { Tone } from '@hackcure/design-system'
import type { HospitalApplication, StepStatus } from './types/onboarding'

export const stepStatusDisplay: Record<StepStatus, { label: string; tone: Tone }> = {
  completed: { label: 'Terminé', tone: 'success' },
  attention: { label: 'Action requise', tone: 'warning' },
  in_progress: { label: 'En cours', tone: 'info' },
  pending: { label: 'À faire', tone: 'neutral' },
  locked: { label: 'Verrouillé', tone: 'neutral' },
}

export const applicationStatusDisplay: Record<HospitalApplication['status'], { label: string; tone: Tone }> = {
  draft: { label: 'Inscription enregistrée', tone: 'neutral' },
  pending: { label: 'Soumise', tone: 'neutral' },
  human_review: { label: 'En revue humaine', tone: 'info' },
  approved: { label: 'Approuvée', tone: 'success' },
  rejected: { label: 'Rejetée', tone: 'danger' },
}

const dateTimeFormat = new Intl.DateTimeFormat('fr-TN', {
  dateStyle: 'medium',
  timeStyle: 'short',
  hourCycle: 'h23',
  timeZone: 'Africa/Tunis',
})

export function formatDateTime(iso: string): string {
  return dateTimeFormat.format(new Date(iso))
}
