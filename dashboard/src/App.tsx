import React, { useState } from 'react'
import Nav from './components/Nav'
import Footer from './components/Footer'
import DashboardPage from './pages/DashboardPage'
import SegmentsPage from './pages/SegmentsPage'
import SegmentBuilderPage from './pages/SegmentBuilderPage'
import SegmentDetailPage from './pages/SegmentDetailPage'
import { Segment } from './components/SegmentCard'

export type Page = 'dashboard' | 'segments' | 'segment-builder' | 'segment-detail'

export default function App(): React.JSX.Element {
  const [page, setPage]               = useState<Page>('dashboard')
  const [activeSegment, setActiveSegment] = useState<Segment | null>(null)

  // All hooks must be called before any conditional render.
  const renderPage = (): React.JSX.Element => {
    switch (page) {
      case 'dashboard':
        return <DashboardPage />

      case 'segments':
        return (
          <SegmentsPage
            onCreateNew={() => setPage('segment-builder')}
            onViewDetail={(id) => {
              // In Sprint 6 this will fetch from the API; for now use stub
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
