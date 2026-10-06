import { useEffect, useMemo, useRef, useState } from 'react'
import { formatPower, formatTime } from '../../lib/format'

const HEIGHT = 230
const PAD = { top: 16, right: 16, bottom: 28, left: 64 }
const LINE = '#38bdf8'

function useWidth(ref) {
  const [width, setWidth] = useState(640)
  useEffect(() => {
    if (!ref.current) return undefined
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width))
    observer.observe(ref.current)
    return () => observer.disconnect()
  }, [ref])
  return width
}

function niceMax(value) {
  if (value <= 0) return 10
  const magnitude = 10 ** Math.floor(Math.log10(value))
  return Math.ceil((value * 1.15) / magnitude) * magnitude
}

/** Total power over the samples this browser has collected (one series, so no legend). */
export function PowerLineChart({ samples, markers = [] }) {
  const container = useRef(null)
  const width = useWidth(container)
  const [hover, setHover] = useState(null)

  const geometry = useMemo(() => {
    if (samples.length < 2) return null
    const t0 = samples[0].t
    const t1 = samples.at(-1).t
    const yMax = niceMax(Math.max(...samples.map((s) => s.totalW)))
    const innerW = Math.max(10, width - PAD.left - PAD.right)
    const innerH = HEIGHT - PAD.top - PAD.bottom
    const x = (t) => PAD.left + ((t - t0) / Math.max(1, t1 - t0)) * innerW
    const y = (w) => PAD.top + innerH - (w / yMax) * innerH
    const points = samples.map((s) => [x(s.t), y(s.totalW)])
    const line = points.map(([px, py], i) => `${i ? 'L' : 'M'}${px.toFixed(1)},${py.toFixed(1)}`).join('')
    const area = `${line}L${points.at(-1)[0]},${y(0)}L${points[0][0]},${y(0)}Z`
    const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => ({ value: yMax * f, y: y(yMax * f) }))
    // Real anomaly timestamps from the backend, drawn only when they fall inside the sampled window.
    const anomalyMarks = markers.filter((m) => m.t >= t0 && m.t <= t1).map((m) => ({ ...m, x: x(m.t) }))
    return { points, line, area, ticks, x, y, innerW, anomalyMarks }
  }, [samples, width, markers])

  if (!geometry) {
    return (
      <div ref={container} className="grid h-[230px] place-items-center text-sm text-slate-500">
        Collecting samples… the first points appear within 10 seconds.
      </div>
    )
  }

  const onMove = (event) => {
    const rect = event.currentTarget.getBoundingClientRect()
    const px = event.clientX - rect.left
    let nearest = 0
    geometry.points.forEach(([x], i) => {
      if (Math.abs(x - px) < Math.abs(geometry.points[nearest][0] - px)) nearest = i
    })
    setHover(nearest)
  }
  const hovered = hover != null ? samples[hover] : null
  const hoverPoint = hover != null ? geometry.points[hover] : null

  return (
    <div ref={container} className="relative">
      <svg width={width} height={HEIGHT} role="img" aria-label="Total power draw over time">
        <defs>
          <linearGradient id="power-area" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={LINE} stopOpacity="0.22" />
            <stop offset="100%" stopColor={LINE} stopOpacity="0" />
          </linearGradient>
        </defs>
        {geometry.ticks.map((tick) => (
          <g key={tick.value}>
            <line x1={PAD.left} x2={width - PAD.right} y1={tick.y} y2={tick.y} stroke="rgba(148,163,184,0.12)" />
            <text x={PAD.left - 8} y={tick.y + 4} textAnchor="end" fontSize="11" fill="#94a3b8">
              {formatPower(tick.value)}
            </text>
          </g>
        ))}
        {[0, Math.floor(samples.length / 2), samples.length - 1].map((i) => (
          <text key={i} x={geometry.points[i][0]} y={HEIGHT - 8} textAnchor="middle" fontSize="11" fill="#94a3b8">
            {formatTime(new Date(samples[i].t).toISOString())}
          </text>
        ))}
        <path d={geometry.area} fill="url(#power-area)" />
        {geometry.anomalyMarks.map((mark) => (
          <g key={`${mark.t}-${mark.label}`}>
            <line x1={mark.x} x2={mark.x} y1={PAD.top} y2={HEIGHT - PAD.bottom} stroke="#f87171" strokeWidth="1.5" strokeDasharray="4 3" />
            <circle cx={mark.x} cy={PAD.top + 4} r="4" fill="#f87171" stroke="#030712" strokeWidth="2">
              <title>Isolation Forest anomaly · {mark.label}</title>
            </circle>
          </g>
        ))}
        <path d={geometry.line} fill="none" stroke={LINE} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
        <circle cx={geometry.points.at(-1)[0]} cy={geometry.points.at(-1)[1]} r="4" fill={LINE} stroke="#030712" strokeWidth="2" />
        {hoverPoint && (
          <g pointerEvents="none">
            <line x1={hoverPoint[0]} x2={hoverPoint[0]} y1={PAD.top} y2={HEIGHT - PAD.bottom} stroke="rgba(226,232,240,0.35)" strokeDasharray="3 3" />
            <circle cx={hoverPoint[0]} cy={hoverPoint[1]} r="5" fill={LINE} stroke="#030712" strokeWidth="2" />
          </g>
        )}
        <rect
          x={PAD.left}
          y={PAD.top}
          width={geometry.innerW}
          height={HEIGHT - PAD.top - PAD.bottom}
          fill="transparent"
          onPointerMove={onMove}
          onPointerLeave={() => setHover(null)}
        />
      </svg>
      {hovered && (
        <div
          className="chart-tooltip"
          style={{ left: Math.min(hoverPoint[0] + 12, width - 170), top: Math.max(0, hoverPoint[1] - 56) }}
        >
          <p className="text-slate-400">{formatTime(new Date(hovered.t).toISOString())}</p>
          <p className="font-semibold text-white">{formatPower(hovered.totalW)}</p>
        </div>
      )}
      <details className="mt-2 text-xs text-slate-400">
        <summary className="cursor-pointer select-none">View as table</summary>
        <table className="mt-2 w-full max-w-sm text-left">
          <thead>
            <tr className="text-slate-500">
              <th className="py-1 font-medium">Time</th>
              <th className="py-1 font-medium">Total power</th>
            </tr>
          </thead>
          <tbody>
            {[...samples].reverse().slice(0, 30).map((s) => (
              <tr key={s.t}>
                <td className="py-0.5 tabular-nums">{formatTime(new Date(s.t).toISOString())}</td>
                <td className="py-0.5 tabular-nums">{formatPower(s.totalW)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  )
}
