import React, { Suspense, lazy, useState } from 'react'
import Nav from './components/Nav'
import Footer from './components/Footer'
import DashboardPage from './pages/DashboardPage'
import SegmentsPage from './pages/SegmentsPage'
import SegmentBuilderPage from './pages/SegmentBuilderPage'
import SegmentDetailPage from './pages/SegmentDetailPage'
import CampaignLauncherPage from './pages/CampaignLauncherPage'
import SimulationResultsPage from './pages/SimulationResultsPage'
import AdminPage from './pages/AdminPage'
import LoginPage from './pages/LoginPage'
import { useCampaignStore } from './store/campaignStore'
import { useAuthStore } from './store/authStore'
import { Segment } from './components/SegmentCard'

// Analytics pulls in the charting library and Info is a long static page;
// loading them on demand keeps both out of the initial bundle.
const AnalyticsPage = lazy(() => import('./pages/AnalyticsPage'))
const InfoPage = lazy(() => import('./pages/InfoPage'))

const _AUTH_REQUIRED = import.meta.env.VITE_AUTH_REQUIRED === 'true'

export type Page =
  | 'dashboard'
  | 'segments'
  | 'segment-builder'
  | 'segment-detail'
  | 'campaign-launcher'
  | 'simulation-results'
  | 'analytics'
  | 'admin'
  | 'info'
  | 'login'

export default function App(): React.JSX.Element {
  const [page, setPage]               = useState<Page>('dashboard')
  const [activeSegment, setActiveSegment] = useState<Segment | null>(null)

  const { resetForm } = useCampaignStore()
  const token = useAuthStore((s) => s.token)

  // Redirect to login if auth is required and no token is present
  if (_AUTH_REQUIRED && !token) {
    return <LoginPage />
  }

  const renderPage = (): React.JSX.Element => {
    switch (page) {
      case 'dashboard':
        return <DashboardPage />

      case 'segments':
        return (
          <SegmentsPage
            onCreateNew={() => setPage('segment-builder')}
            onViewDetail={(segment) => {
              setActiveSegment(segment)
              setPage('segment-detail')
            }}
          />
        )

      case 'segment-builder':
        return (
          <SegmentBuilderPage
            onCancel={() => setPage('segments')}
            onSaved={() => setPage('segments')}
          />
        )

      case 'segment-detail':
        return activeSegment ? (
          <SegmentDetailPage
            segment={activeSegment}
            onBack={() => setPage('segments')}
          />
        ) : (
          <SegmentsPage
            onCreateNew={() => setPage('segment-builder')}
            onViewDetail={(segment) => setActiveSegment(segment)}
          />
        )

      case 'campaign-launcher':
        return (
          <CampaignLauncherPage
            onLaunchComplete={() => setPage('simulation-results')}
            onCancel={() => setPage('dashboard')}
          />
        )

      case 'simulation-results':
        return (
          <SimulationResultsPage
            onLaunchAnother={() => {
              resetForm()
              setPage('campaign-launcher')
            }}
            onViewSegments={() => setPage('segments')}
          />
        )

      case 'analytics':
        return <AnalyticsPage />

      case 'admin':
        return <AdminPage />

      case 'info':
        return <InfoPage />

      case 'login':
        return <LoginPage />
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Nav currentPage={page} onNavigate={setPage} />
      <main style={{ flex: 1 }}>
        <Suspense fallback={null}>{renderPage()}</Suspense>
      </main>
      <Footer />
    </div>
  )
}
