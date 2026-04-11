import { Loader } from 'lucide-react'
import './AgentStatus.css'

interface Agent {
  id: string
  name: string
  status: 'idle' | 'running' | 'blocked' | 'stopped'
  currentTask: string | null
  progress: number
}

interface AgentStatusProps {
  agent: Agent
}

export default function AgentStatus({ agent }: AgentStatusProps) {
  return (
    <div className={`agent-card ${agent.status}`}>
      <div className="agent-header">
        <span className="agent-name">{agent.name}</span>
        <span className={`status-badge ${agent.status}`}>
          {agent.status === 'running' && <Loader size={12} className="spin" />}
          {agent.status}
        </span>
      </div>
      {agent.currentTask && (
        <div className="agent-task">
          <span className="task-label">Current Task:</span>
          <span className="task-name">{agent.currentTask}</span>
        </div>
      )}
      {agent.status === 'running' && (
        <div className="agent-progress">
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${agent.progress}%` }} />
          </div>
          <span className="progress-text">{agent.progress}%</span>
        </div>
      )}
    </div>
  )
}
