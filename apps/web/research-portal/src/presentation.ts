import type { Tone } from '@hackcure/design-system'
import type { PageStatus, ResearchAccessRequest } from './types/research'

export const requestStatusDisplay: Record<ResearchAccessRequest['status'] | 'not_submitted', { label: string; tone: Tone }> = {
  not_submitted: { label: 'Non soumise', tone: 'neutral' },
  under_review: { label: 'En revue', tone: 'info' },
  approved: { label: 'Autorisée', tone: 'success' },
  rejected: { label: 'Refusée', tone: 'danger' },
}

export const pageStatusDisplay: Record<PageStatus, { label: string; tone: Tone }> = {
  available: { label: 'Accessible', tone: 'neutral' },
  locked: { label: 'Verrouillé', tone: 'neutral' },
}

const dateFormat = new Intl.DateTimeFormat('fr-TN', { dateStyle: 'medium', timeZone: 'Africa/Tunis' })

const dateTimeFormat = new Intl.DateTimeFormat('fr-TN', {
  dateStyle: 'medium',
  timeStyle: 'short',
  hourCycle: 'h23',
  timeZone: 'Africa/Tunis',
})

export function formatDate(iso: string): string {
  return dateFormat.format(new Date(iso))
}

export function formatDateTime(iso: string): string {
  return dateTimeFormat.format(new Date(iso))
}
