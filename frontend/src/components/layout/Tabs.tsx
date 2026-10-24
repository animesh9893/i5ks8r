import { NavLink } from 'react-router-dom'

const TABS = [
  { to: '/day-ahead', label: 'Day-Ahead Planner' },
  { to: '/forecast-vs-actual', label: 'Forecast vs Actual' },
  { to: '/accuracy', label: 'Accuracy' },
]

export default function Tabs() {
  return (
    <nav className="mb-6 flex gap-1 border-b border-slate-200">
      {TABS.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          className={({ isActive }) =>
            `-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
              isActive
                ? 'border-forecast text-forecast'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`
          }
        >
          {tab.label}
        </NavLink>
      ))}
    </nav>
  )
}
