import { useEffect, useState } from 'react'
import { AppShell, Badge, SideNav, ThemeToggle, type SideNavItem } from '@hackcure/design-system'
import { HOSPITAL } from './services/hospital'
import { loadPatients, type Patient } from './services/patientService'
import { loadStaff, type StaffMember } from './services/staffService'
import { PatientsView } from './views/PatientsView'
import { StaffView } from './views/StaffView'

type ViewId = 'personnel' | 'patients'

function viewFromHash(): ViewId {
  return window.location.hash === '#patients' ? 'patients' : 'personnel'
}

export default function App() {
  const [currentView, setCurrentView] = useState<ViewId>(viewFromHash)
  // Fictional fixtures; local changes live in memory only and reset on reload.
  const [staff, setStaff] = useState<StaffMember[]>(loadStaff)
  const [patients, setPatients] = useState<Patient[]>(loadPatients)

  useEffect(() => {
    const handleHashChange = () => setCurrentView(viewFromHash())
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  const navItem = (view: ViewId, label: string, count: number): SideNavItem => ({
    label,
    href: `#${view}`,
    current: currentView === view,
    badge: <Badge>{count}</Badge>,
  })

  return (
    <AppShell
      productName="Portail Hospitalier"
      productContext={HOSPITAL.name}
      navigation={
        <SideNav
          label="Navigation principale"
          sections={[
            {
              items: [
                navItem('personnel', 'Gestion du personnel', staff.filter((s) => s.status === 'active').length),
                navItem('patients', 'Gestion des patients', patients.length),
              ],
            },
          ]}
        />
      }
      toolbar={<ThemeToggle />}
      pageKey={currentView}
      sidebarFooter={
        <div className="space-y-1">
          <div className="font-semibold text-ink">{HOSPITAL.shortName}</div>
          <div className="text-ink-muted">Données fictives, conservées en mémoire</div>
        </div>
      }
    >
      {currentView === 'personnel' ? (
        <StaffView staff={staff} onChange={setStaff} />
      ) : (
        <PatientsView patients={patients} onChange={setPatients} />
      )}
    </AppShell>
  )
}
