import { useState, useEffect } from 'react'
import { Play, Square, RefreshCw, CheckCircle, XCircle, Loader } from 'lucide-react'
import Console from '../components/Console'
import AgentStatus from '../components/AgentStatus'
import TaskBoard from '../components/TaskBoard'
import './Execution.css'

export default function Execution() {
  const [isRunning, setIsRunning] = useState(false)
  const [progress, setProgress] = useState(65)

  const agents = [
    { id: 'agent-1', name: 'Agent #1', status: 'running', currentTask: 'Task #4', progress: 80 },
    { id: 'agent-2', name: 'Agent #2', status: 'idle', currentTask: null, progress: 0 },
    { id: 'agent-3', name: 'Agent #3', status: 'blocked', currentTask: 'Task #8', progress: 30 },
  ]

  const logs = [
    { timestamp: '10:42:15', level: 'info', message: 'Starting task execution...' },
    { timestamp: '10:42:16', level: 'info', message: 'Agent #1 assigned to Task #4' },
    { timestamp: '10:42:18', level: 'info', message: 'Agent #2 idle, waiting for available task' },
    { timestamp: '10:43:22', level: 'warning', message: 'Agent #3 blocked on Task #8: dependency not ready' },
    { timestamp: '10:44:01', level: 'success', message: 'Task #4 step 1 completed: Code generated' },
    { timestamp: '10:44:15', level: 'info', message: 'Running lint validation...' },
    { timestamp: '10:44:18', level: 'success', message: 'Lint passed' },
    { timestamp: '10:44:20', level: 'info', message: 'Running build...' },
    { timestamp: '10:44:35', level: 'success', message: 'Build successful' },
  ]

  return (
    <div className="execution">
      <header className="page-header">
        <div className="header-left">
          <h2>Execution</h2>
          <p className="subtitle">Real-time task execution monitoring</p>
        </div>
        <div className="header-actions">
          <button
            className={`btn ${isRunning ? 'danger' : 'primary'}`}
            onClick={() => setIsRunning(!isRunning)}
          >
            {isRunning ? <Square size={16} /> : <Play size={16} />}
            {isRunning ? 'Stop' : 'Start'}
          </button>
          <button className="btn">
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>
      </header>

      <div className="execution-progress">
        <div className="progress-info">
          <span className="progress-label">Overall Progress</span>
          <span className="progress-value">{progress}%</span>
        </div>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${progress}%` }} />
        </div>
        <div className="progress-stats">
          <span><CheckCircle size={14} className="success" /> 11 completed</span>
          <span><Loader size={14} className="running" /> 3 in progress</span>
          <span><XCircle size={14} className="blocked" /> 1 blocked</span>
        </div>
      </div>

      <div className="execution-grid">
        <section className="execution-agents">
          <h3>Agents</h3>
          <div className="agents-list">
            {agents.map((agent) => (
              <AgentStatus key={agent.id} agent={agent} />
            ))}
          </div>
        </section>

        <section className="execution-tasks">
          <h3>Tasks</h3>
          <TaskBoard />
        </section>

        <section className="execution-console">
          <h3>Console</h3>
          <Console logs={logs} />
        </section>
      </div>
    </div>
  )
}
