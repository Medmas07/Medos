import type { Tone } from '@hackcure/design-system'
import type { SciAgentsInvestigation } from '../types/research'

export interface InvestigationProgressDisplay {
  label: string
  detail: string
  percent: number | null
  tone: Tone
}

/** Builds a truthful display model without inventing progress SciAgents did not report. */
export function investigationProgressDisplay(
  investigation: Pick<SciAgentsInvestigation, 'status' | 'progress'>,
): InvestigationProgressDisplay {
  const reported = investigation.progress

  if (investigation.status === 'queued') {
    return {
      label: reported?.stageLabel ?? 'En attente de SciAgents',
      detail: "La demande est acceptée et attend le début de l'exécution.",
      percent: reported?.percent ?? null,
      tone: 'neutral',
    }
  }
  if (investigation.status === 'running') {
    return {
      label: reported?.stageLabel ?? 'Exécution SciAgents',
      detail:
        reported?.percent === null || reported?.percent === undefined
          ? "SciAgents n'a fourni aucune estimation de fin ; l'étape affichée est la dernière connue."
          : `Progression estimée par l'adaptateur : ${reported.percent} %.`,
      percent: reported?.percent ?? null,
      tone: 'info',
    }
  }
  if (investigation.status === 'completed') {
    return {
      label: reported?.stageLabel ?? 'Terminée',
      detail: "L'exécution est terminée ; le résultat contrôlé par l'adaptateur peut être examiné.",
      percent: 100,
      tone: 'success',
    }
  }
  return {
    label: reported?.stageLabel ?? 'Exécution interrompue',
    detail: "L'exécution s'est arrêtée sans produire de résultat affichable.",
    percent: null,
    tone: 'danger',
  }
}
