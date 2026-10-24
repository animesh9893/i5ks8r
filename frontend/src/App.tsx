import { Navigate, Route, Routes } from 'react-router-dom'
import Header from './components/layout/Header'
import Tabs from './components/layout/Tabs'
import DayAheadPage from './pages/DayAheadPage'
import ForecastVsActualPage from './pages/ForecastVsActualPage'
import AccuracyPage from './pages/AccuracyPage'

export default function App() {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Tabs />
        <Routes>
          <Route path="/" element={<Navigate to="/day-ahead" replace />} />
          <Route path="/day-ahead" element={<DayAheadPage />} />
          <Route path="/forecast-vs-actual" element={<ForecastVsActualPage />} />
          <Route path="/accuracy" element={<AccuracyPage />} />
          <Route path="*" element={<Navigate to="/day-ahead" replace />} />
        </Routes>
      </main>
    </div>
  )
}
