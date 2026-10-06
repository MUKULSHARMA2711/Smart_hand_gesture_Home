import { useState } from 'react'
import { motion } from 'motion/react'
import { formatPower } from '../../lib/format'

/** Current power per device — one magnitude series, one hue, bars sorted by value. */
export function DevicePowerBars({ devices, total }) {
  const [hovered, setHovered] = useState(null)
  const rows = [...devices].sort((a, b) => b.power_w - a.power_w)
  const max = Math.max(1, ...rows.map((d) => d.power_w))

  return (
    <ul className="space-y-2" aria-label="Current power by device">
      {rows.map((device) => {
        const share = total ? Math.round((100 * device.power_w) / total) : 0
        return (
          <li
            key={device.id}
            className="relative grid grid-cols-[8.5rem_1fr_5.5rem] items-center gap-3 text-sm"
            onPointerEnter={() => setHovered(device.id)}
            onPointerLeave={() => setHovered(null)}
          >
            <span className="truncate text-slate-300">{device.name}</span>
            <span className="relative h-5">
              <motion.span
                className="absolute inset-y-0 left-0 rounded-r-[4px] bg-sky-400"
                initial={false}
                animate={{ width: `${Math.max(0.8, (100 * device.power_w) / max)}%` }}
                transition={{ duration: 0.6, ease: 'easeOut' }}
              />
            </span>
            <span className="text-right text-slate-300 tabular-nums">{formatPower(device.power_w)}</span>
            {hovered === device.id && (
              <span className="chart-tooltip pointer-events-none" style={{ left: '9rem', top: '-2.6rem' }}>
                <span className="block text-slate-400">{device.name}</span>
                <span className="block font-semibold text-white">
                  {formatPower(device.power_w)} · {share}% of total
                </span>
              </span>
            )}
          </li>
        )
      })}
    </ul>
  )
}
