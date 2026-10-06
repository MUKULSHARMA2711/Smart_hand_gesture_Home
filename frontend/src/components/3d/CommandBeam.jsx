import { useMemo, useRef } from 'react'
import { Line } from '@react-three/drei'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { BEAM_TRAVEL_MS } from '../../state/aiLifecycle'
import { Halo } from './glow'
import { COLORS } from './palette'

const FADE_MS = 900
// A rejected/failed command stops short of the device and fizzles out in red.
const REJECTED_STOP = 0.8

/**
 * An energy path from an input (AI core or gesture) to a device, for one *real*
 * command result. `status` comes from the backend: executed, rejected or failed.
 */
export function CommandBeam({ from, to, color, status, startAt, reducedMotion }) {
  const succeeded = status === 'executed'
  const curve = useMemo(() => {
    const start = new THREE.Vector3(...from)
    const end = new THREE.Vector3(...to)
    const mid = start.clone().lerp(end, 0.5)
    mid.y = Math.max(start.y, end.y) + 1.2
    return new THREE.QuadraticBezierCurve3(start, mid, end)
  }, [from, to])
  const points = useMemo(() => curve.getPoints(40), [curve])
  const line = useRef()
  const head = useRef()
  const headHalo = useRef()
  const impact = useRef()

  useFrame(() => {
    const elapsed = performance.now() - startAt
    const visible = elapsed >= 0
    const travel = reducedMotion ? 1 : Math.min(1, Math.max(0, elapsed / BEAM_TRAVEL_MS))
    const stop = succeeded ? 1 : REJECTED_STOP
    const progress = Math.min(travel, stop)
    const after = Math.max(0, elapsed - BEAM_TRAVEL_MS) / FADE_MS // 0 → 1 once landed

    if (line.current) {
      line.current.visible = visible
      const material = line.current.material
      material.opacity = visible ? 0.75 * (1 - Math.min(1, after)) : 0
      material.dashOffset -= 0.04
    }
    const position = curve.getPoint(progress)
    if (head.current) {
      head.current.visible = visible && after < 1
      head.current.position.copy(position)
    }
    if (headHalo.current) {
      headHalo.current.visible = visible && after < 1
      headHalo.current.position.copy(position)
      const failed = !succeeded && travel >= stop
      headHalo.current.material.color.set(failed ? COLORS.danger : color)
      headHalo.current.scale.setScalar(failed ? 0.7 + after * 1.2 : 0.7)
      headHalo.current.material.opacity = 1 - Math.min(1, after)
    }
    if (impact.current) {
      impact.current.visible = succeeded && travel >= 1 && after < 1
      impact.current.scale.setScalar(0.6 + after * 2.4)
      impact.current.material.opacity = (1 - after) * 0.9
    }
  })

  return (
    <group>
      <Line ref={line} points={points} color={color} lineWidth={2} dashed dashSize={0.25} gapSize={0.12} transparent opacity={0} toneMapped={false} />
      <mesh ref={head} visible={false}>
        <sphereGeometry args={[0.07, 12, 12]} />
        <meshBasicMaterial color="#ffffff" toneMapped={false} />
      </mesh>
      <Halo ref={headHalo} color={color} opacity={0} scale={0.7} visible={false} />
      <Halo ref={impact} position={to} color={color} opacity={0} scale={0.6} visible={false} />
    </group>
  )
}

/** Dashboard commands have no beam: a short pulse on the device shows the confirmed change. */
export function ImpactPulse({ at, color, startAt }) {
  const halo = useRef()
  useFrame(() => {
    if (!halo.current) return
    const p = Math.min(1, Math.max(0, (performance.now() - startAt) / 1100))
    halo.current.visible = p > 0 && p < 1
    halo.current.scale.setScalar(0.6 + p * 2.2)
    halo.current.material.opacity = (1 - p) * 0.8
  })
  return <Halo ref={halo} position={at} color={color} opacity={0} visible={false} />
}
