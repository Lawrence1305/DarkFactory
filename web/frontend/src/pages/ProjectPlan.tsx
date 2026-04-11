import { useState } from 'react'
import ReactFlow, { Node, Edge, Background, Controls } from 'reactflow'
import 'reactflow/dist/style.css'
import { Plus, GitBranch, Calendar, AlertTriangle } from 'lucide-react'
import GanttChart from '../components/GanttChart'
import './ProjectPlan.css'

interface TaskNode {
  id: string
  title: string
  duration: number
  status: 'pending' | 'in_progress' | 'completed' | 'blocked'
  dependencies: string[]
  priority: number
}

const mockTasks: TaskNode[] = [
  { id: '1', title: 'Initialize Project', duration: 30, status: 'completed', dependencies: [], priority: 1 },
  { id: '2', title: 'Setup Agent Pool', duration: 60, status: 'in_progress', dependencies: ['1'], priority: 1 },
  { id: '3', title: 'Implement Memory System', duration: 90, status: 'pending', dependencies: ['1'], priority: 2 },
  { id: '4', title: 'Create Skill Generator', duration: 45, status: 'pending', dependencies: ['2', '3'], priority: 2 },
  { id: '5', title: 'Build Web UI', duration: 120, status: 'pending', dependencies: ['2'], priority: 3 },
]

const mockEdges: Edge[] = [
  { id: 'e1-2', source: '1', target: '2', animated: false },
  { id: 'e1-3', source: '1', target: '3', animated: false },
  { id: 'e2-4', source: '2', target: '4', animated: true },
  { id: 'e3-4', source: '3', target: '4', animated: false },
  { id: 'e2-5', source: '2', target: '5', animated: false },
]

export default function ProjectPlan() {
  const [view, setView] = useState<'network' | 'gantt'>('network')
  const [criticalPath, setCriticalPath] = useState<string[]>(['1', '2', '4'])

  const flowNodes: Node[] = mockTasks.map((task) => ({
    id: task.id,
    data: { label: task.title, status: task.status, duration: task.duration },
    position: { x: 0, y: 0 },
    type: 'default',
    style: {
      background: task.status === 'completed' ? 'var(--accent-green)' :
                 task.status === 'in_progress' ? 'var(--accent-blue)' :
                 task.status === 'blocked' ? 'var(--accent-red)' : 'var(--bg-tertiary)',
      border: criticalPath.includes(task.id) ? '2px solid var(--accent-yellow)' : '1px solid var(--border-color)',
      borderRadius: '8px',
      padding: '12px 16px',
      color: 'var(--text-primary)',
      minWidth: '150px',
    },
  }))

  return (
    <div className="project-plan">
      <header className="page-header">
        <div className="header-left">
          <h2>Project Plan</h2>
          <p className="subtitle">Activity Network & Critical Path</p>
        </div>
        <div className="header-actions">
          <button className={`btn ${view === 'network' ? 'active' : ''}`} onClick={() => setView('network')}>
            <GitBranch size={16} /> Network
          </button>
          <button className={`btn ${view === 'gantt' ? 'active' : ''}`} onClick={() => setView('gantt')}>
            <Calendar size={16} /> Gantt
          </button>
          <button className="btn primary">
            <Plus size={16} /> Add Task
          </button>
        </div>
      </header>

      <div className="plan-info">
        <div className="critical-path-info">
          <AlertTriangle size={16} />
          <span>Critical Path: {criticalPath.map(id => `#${id}`).join(' → ')}</span>
        </div>
        <div className="legend">
          <span className="legend-item"><span className="dot green"></span> Completed</span>
          <span className="legend-item"><span className="dot blue"></span> In Progress</span>
          <span className="legend-item"><span className="dot yellow"></span> Critical</span>
          <span className="legend-item"><span className="dot gray"></span> Pending</span>
        </div>
      </div>

      <div className="plan-content">
        {view === 'network' ? (
          <div className="network-view">
            <ReactFlow
              nodes={flowNodes}
              edges={mockEdges}
              background={{ color: 'var(--bg-primary)' }}
              controls={<Controls />}
            >
              <Background color="var(--border-color)" gap={20} />
            </ReactFlow>
          </div>
        ) : (
          <GanttChart tasks={mockTasks} criticalPath={criticalPath} />
        )}
      </div>
    </div>
  )
}
