import React, { useState } from 'react'
import Nav from './components/Nav'
import Footer from './components/Footer'
import DashboardPage from './pages/DashboardPage'

type Page = 'dashboard'

export default function App(): React.JSX.Element {
  const [page, setPage] = useState<Page>('dashboard')

  const renderPage = (): React.JSX.Element => {
    // Conditional render placed after all hooks — React Rules of Hooks.
    switch (page) {
      case 'dashboard':
        return <DashboardPage />
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
