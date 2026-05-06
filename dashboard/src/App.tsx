import React, { useState } from 'react'
import Nav from './components/Nav'
import Footer from './components/Footer'
import DashboardPage from './pages/DashboardPage'
import SegmentsPage from './pages/SegmentsPage'
import SegmentBuilderPage from './pages/SegmentBuilderPage'
import SegmentDetailPage from './pages/SegmentDetailPage'
import CampaignLauncherPage from './pages/CampaignLauncherPage'
import SimulationResultsPage from './pages/SimulationResultsPage'
import AnalyticsPage from './pages/AnalyticsPage'
import LoginPage from './pages/LoginPage'
import { useCampaignStore } from './store/campaignStore'
import { useAuthStore } from './store/authStore'
import { Segment } from './components/SegmentCard'

const _AUTH_REQUIRED = import.meta.env.VITE_AUTH_REQUIRED === 'true'

export type Page =
  | 'dashboard'
  | 'segments'
  | 'segment-builder'
  | 'segment-detail'
  | 'campaign-launcher'
  | 'simulation-results'
  | 'analytics'
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
            onViewDetail={(id) => {
              const stub: Segment = {
                id,
                name: 'Gen Z — Madrid',
                description: 'Urban young adults with high digital engagement.',
                definition: {
                  age_range: { min_age: 18, max_age: 24 },
                  geo: { city: 'Madrid', country: 'Spain' },
                  category_affinities: ['Electronics', 'Fashion'],
                  purchase_history_days: 90,
                },
                is_stale: false,
                last_trained_at: '2026-05-05T10:00:00Z',
                created_at: '2026-05-01T09:00:00Z',
              }
              setActiveSegment(stub)
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
        if (!activeSegment) { setPage('segments'); return <></> }
        return (
          <SegmentDetailPage
            segment={activeSegment}
            onBack={() => setPage('segments')}
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

      case 'login':
        return <LoginPage />
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Nav currentPage={page} onNavigate={setPage} />
      <main style={{ flex: 1 }}>{renderPage()}</main>
      <Footer />
    </div>
  )
}
