import { useRef, useEffect } from 'react'
import { Info, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'
import './Console.css'

interface Log {
  timestamp: string
  level: 'info' | 'warning' | 'success' | 'error'
  message: string
}

interface ConsoleProps {
  logs: Log[]
}

export default function Console({ logs }: ConsoleProps) {
  const consoleRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight
    }
  }, [logs])

  const getIcon = (level: string) => {
    switch (level) {
      case 'warning':
        return <AlertTriangle size={14} />
      case 'success':
        return <CheckCircle size={14} />
      case 'error':
        return <XCircle size={14} />
      default:
        return <Info size={14} />
    }
  }

  return (
    <div className="console" ref={consoleRef}>
      <div className="console-content">
        {logs.map((log, index) => (
          <div key={index} className={`log-entry ${log.level}`}>
            <span className="log-timestamp">{log.timestamp}</span>
            <span className="log-icon">{getIcon(log.level)}</span>
            <span className="log-message">{log.message}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
