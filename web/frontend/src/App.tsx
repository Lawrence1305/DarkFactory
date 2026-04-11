import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { LayoutDashboard, GitBranch, Play, Settings } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import ProjectPlan from './pages/ProjectPlan'
import Execution from './pages/Execution'
import SettingsPage from './pages/Settings'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <nav className="sidebar">
          <div className="sidebar-header">
            <h1 className="logo">DarkFactory</h1>
            <span className="version">v1.0.0</span>
          </div>

          <div className="nav-links">
            <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <LayoutDashboard size={20} />
              <span>Dashboard</span>
            </NavLink>
            <NavLink to="/plan" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <GitBranch size={20} />
              <span>Project Plan</span>
            </NavLink>
            <NavLink to="/execution" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <Play size={20} />
              <span>Execution</span>
            </NavLink>
            <NavLink to="/settings" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <Settings size={20} />
              <span>Settings</span>
            </NavLink>
          </div>

          <div className="sidebar-footer">
            <div className="status-indicator">
              <span className="status-dot online"></span>
              <span>System Online</span>
            </div>
          </div>
        </nav>

        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/plan" element={<ProjectPlan />} />
            <Route path="/execution" element={<Execution />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
