import { CheckCircle, Loader, XCircle, Clock } from 'lucide-react'
import './TaskBoard.css'

interface Task {
  id: string
  title: string
  status: 'pending' | 'in_progress' | 'completed' | 'blocked'
  priority: number
}

const mockTasks: Task[] = [
  { id: '1', title: 'Initialize Project', status: 'completed', priority: 1 },
  { id: '2', title: 'Setup Agent Pool', status: 'in_progress', priority: 1 },
  { id: '3', title: 'Memory System', status: 'completed', priority: 2 },
  { id: '4', title: 'Skill Generator', status: 'in_progress', priority: 2 },
  { id: '5', title: 'Web UI', status: 'pending', priority: 3 },
  { id: '6', title: 'Plugin System', status: 'completed', priority: 2 },
  { id: '7', title: 'Validation Layer', status: 'blocked', priority: 3 },
  { id: '8', title: 'Context Manager', status: 'pending', priority: 2 },
]

export default function TaskBoard() {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle size={16} className="status-icon completed" />
      case 'in_progress':
        return <Loader size={16} className="status-icon running" />
      case 'blocked':
        return <XCircle size={16} className="status-icon blocked" />
      default:
        return <Clock size={16} className="status-icon pending" />
    }
  }

  const getPriorityLabel = (priority: number) => {
    switch (priority) {
      case 1:
        return 'P1'
      case 2:
        return 'P2'
      default:
        return 'P3'
    }
  }

  return (
    <div className="task-board">
      {mockTasks.map((task) => (
        <div key={task.id} className={`task-card ${task.status}`}>
          <div className="task-header">
            <span className="task-id">#{task.id}</span>
            <span className={`priority ${task.priority}`}>{getPriorityLabel(task.priority)}</span>
          </div>
          <div className="task-title">{task.title}</div>
          <div className="task-footer">
            {getStatusIcon(task.status)}
            <span className={`status-text ${task.status}`}>{task.status.replace('_', ' ')}</span>
          </div>
        </div>
      ))}
    </div>
  )
}
