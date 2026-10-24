import { Navigate, Route, Routes } from 'react-router-dom'
import DataGate from './components/layout/DataGate'
import Header from './components/layout/Header'
import Tabs from './components/layout/Tabs'
import AccuracyPage from './pages/AccuracyPage'
import DayAheadPage from './pages/DayAheadPage'
import ForecastVsActualPage from './pages/ForecastVsActualPage'

export default function App() {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Tabs />
        <DataGate>
          {(meta) => (
            <Routes>
              <Route path="/" element={<Navigate to="/day-ahead" replace />} />
              <Route path="/day-ahead" element={<DayAheadPage meta={meta} />} />
              <Route path="/forecast-vs-actual" element={<ForecastVsActualPage meta={meta} />} />
              <Route path="/accuracy" element={<AccuracyPage meta={meta} />} />
              <Route path="*" element={<Navigate to="/day-ahead" replace />} />
            </Routes>
          )}
        </DataGate>
        <footer className="mt-10 border-t border-line pt-4 text-xs text-muted">
          Wind actuals: Elexon FUELHH (fuel type WIND, half-hourly). Forecasts: Elexon WINDFOR (hourly). Times
          shown in UK local time. Error = forecast − actual.
        </footer>
      </main>
    </div>
  )
}
