import { NavLink, useLocation } from 'react-router-dom'

const TABS = [
  { to: '/day-ahead', label: 'Day-Ahead Planner' },
  { to: '/forecast-vs-actual', label: 'Forecast vs Actual' },
  { to: '/accuracy', label: 'Accuracy' },
]

export default function Tabs() {
  // Carry filters (from/to/h/day) across tabs.
  const { search } = useLocation()
  return (
    <nav aria-label="Views" className="mb-5 flex gap-1 overflow-x-auto border-b border-line">
      {TABS.map((tab) => (
        <NavLink
          key={tab.to}
          to={{ pathname: tab.to, search }}
          className={({ isActive }) =>
            `-mb-px whitespace-nowrap border-b-2 px-4 py-2 text-sm font-medium ${
              isActive ? 'border-accent text-ink' : 'border-transparent text-ink-2 hover:text-ink'
            }`
          }
        >
          {tab.label}
        </NavLink>
      ))}
    </nav>
  )
}
