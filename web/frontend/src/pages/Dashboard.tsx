import { useState, useEffect } from 'react'
import { Activity, Brain, TrendingUp, Clock, CheckCircle, AlertCircle } from 'lucide-react'
import './Dashboard.css'

interface Project {
  id: string
  name: string
  task_count: number
  completed_count: number
}

interface Stats {
  total_tasks: number
  completed_tasks: number
  active_agents: number
  skills_created: number
}

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([])
  const [stats, setStats] = useState<Stats>({
    total_tasks: 0,
    completed_tasks: 0,
    active_agents: 0,
    skills_created: 0,
  })

  useEffect(() => {
    // Mock data - in production, fetch from API
    setProjects([
      { id: '1', name: 'DarkFactory Core', task_count: 12, completed_count: 8 },
      { id: '2', name: 'Web UI', task_count: 6, completed_count: 3 },
    ])
    setStats({
      total_tasks: 18,
      completed_tasks: 11,
      active_agents: 3,
      skills_created: 5,
    })
  }, [])

  const completionRate = stats.total_tasks > 0
    ? Math.round((stats.completed_tasks / stats.total_tasks) * 100)
    : 0

  return (
    <div className="dashboard">
      <header className="page-header">
        <h2>Dashboard</h2>
        <p className="subtitle">AI-Native Agent Framework Overview</p>
      </header>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon blue">
            <Activity size={24} />
          </div>
          <div className="stat-content">
            <span className="stat-value">{stats.total_tasks}</span>
            <span className="stat-label">Total Tasks</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon green">
            <CheckCircle size={24} />
          </div>
          <div className="stat-content">
            <span className="stat-value">{stats.completed_tasks}</span>
            <span className="stat-label">Completed</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon purple">
            <Brain size={24} />
          </div>
          <div className="stat-content">
            <span className="stat-value">{stats.skills_created}</span>
            <span className="stat-label">Skills Created</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon cyan">
            <TrendingUp size={24} />
          </div>
          <div className="stat-content">
            <span className="stat-value">{completionRate}%</span>
            <span className="stat-label">Progress</span>
          </div>
        </div>
      </div>

      <div className="dashboard-grid">
        <section className="card projects-section">
          <h3>Projects</h3>
          <div className="projects-list">
            {projects.map((project) => (
              <div key={project.id} className="project-item">
                <div className="project-info">
                  <span className="project-name">{project.name}</span>
                  <span className="project-progress">
                    {project.completed_count}/{project.task_count} tasks
                  </span>
                </div>
                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{
                      width: `${(project.completed_count / project.task_count) * 100}%`
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="card activity-section">
          <h3>Recent Activity</h3>
          <div className="activity-list">
            <div className="activity-item">
              <Clock size={16} />
              <span className="activity-text">Task #12 completed: Skill generation</span>
              <span className="activity-time">2m ago</span>
            </div>
            <div className="activity-item">
              <AlertCircle size={16} />
              <span className="activity-text">Agent #2 blocked on Task #8</span>
              <span className="activity-time">5m ago</span>
            </div>
            <div className="activity-item">
              <CheckCircle size={16} />
              <span className="activity-text">Validation passed: Lint + Build</span>
              <span className="activity-time">8m ago</span>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
