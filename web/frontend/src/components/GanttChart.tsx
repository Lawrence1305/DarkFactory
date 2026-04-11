import { useRef, useEffect } from 'react'
import * as d3 from 'd3'
import './GanttChart.css'

interface Task {
  id: string
  title: string
  duration: number
  status: 'pending' | 'in_progress' | 'completed' | 'blocked'
  dependencies: string[]
  priority: number
}

interface GanttChartProps {
  tasks: Task[]
  criticalPath: string[]
}

export default function GanttChart({ tasks, criticalPath }: GanttChartProps) {
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    if (!svgRef.current) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const margin = { top: 40, right: 40, bottom: 40, left: 200 }
    const width = svgRef.current.clientWidth - margin.left - margin.right
    const height = tasks.length * 50 + margin.top + margin.bottom

    const g = svg
      .attr('width', width + margin.left + margin.right)
      .attr('height', height)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`)

    // Calculate total duration
    const maxDuration = d3.max(tasks, (d) => d.duration) || 60

    // Scales
    const xScale = d3.scaleLinear().domain([0, maxDuration]).range([0, width])

    const yScale = d3
      .scaleBand()
      .domain(tasks.map((d) => d.id))
      .range([0, tasks.length * 50])
      .padding(0.3)

    // Grid lines
    g.append('g')
      .attr('class', 'grid')
      .selectAll('line')
      .data(xScale.ticks(10))
      .enter()
      .append('line')
      .attr('x1', (d) => xScale(d))
      .attr('x2', (d) => xScale(d))
      .attr('y1', 0)
      .attr('y2', tasks.length * 50)
      .attr('stroke', 'var(--border-color)')
      .attr('stroke-dasharray', '2,2')

    // Task bars
    const taskGroups = g
      .selectAll('.task')
      .data(tasks)
      .enter()
      .append('g')
      .attr('class', 'task')
      .attr('transform', (_, i) => `translate(0, ${i * 50})`)

    // Task labels
    taskGroups
      .append('text')
      .attr('x', -10)
      .attr('y', yScale.bandwidth() / 2)
      .attr('text-anchor', 'end')
      .attr('dominant-baseline', 'middle')
      .attr('fill', 'var(--text-primary)')
      .attr('font-size', '13px')
      .text((d) => d.title)

    // Duration bars
    taskGroups
      .append('rect')
      .attr('x', 0)
      .attr('y', 0)
      .attr('width', (d) => xScale(d.duration))
      .attr('height', yScale.bandwidth())
      .attr('rx', 4)
      .attr('fill', (d) => {
        if (d.status === 'completed') return 'var(--accent-green)'
        if (d.status === 'in_progress') return 'var(--accent-blue)'
        if (d.status === 'blocked') return 'var(--accent-red)'
        return 'var(--bg-tertiary)'
      })
      .attr('stroke', (d) => (criticalPath.includes(d.id) ? 'var(--accent-yellow)' : 'none'))
      .attr('stroke-width', 2)

    // Duration labels
    taskGroups
      .append('text')
      .attr('x', (d) => xScale(d.duration) - 8)
      .attr('y', yScale.bandwidth() / 2)
      .attr('text-anchor', 'end')
      .attr('dominant-baseline', 'middle')
      .attr('fill', 'white')
      .attr('font-size', '11px')
      .attr('font-weight', '500')
      .text((d) => `${d.duration}m`)

    // Timeline header
    svg
      .append('g')
      .attr('transform', `translate(${margin.left}, 20)`)
      .selectAll('text')
      .data(xScale.ticks(10))
      .enter()
      .append('text')
      .attr('x', (d) => xScale(d))
      .attr('y', 0)
      .attr('text-anchor', 'middle')
      .attr('fill', 'var(--text-muted)')
      .attr('font-size', '11px')
      .text((d) => `${d}m`)
  }, [tasks, criticalPath])

  return (
    <div className="gantt-chart">
      <svg ref={svgRef}></svg>
    </div>
  )
}
