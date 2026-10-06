import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { DeviceShell, useInvalidateOn } from './DeviceShell'
import { FloorGlow, Halo } from './glow'
import { ANCHORS } from './layout'
import { COLORS } from './palette'
import { approach, LIGHT_MAX_POINT_INTENSITY, lightVisual } from './visualState'

/** Floor lamp. Backend brightness drives the bulb, the room light and the floor glow. */
export function Light3D({ device, reducedMotion, ...shell }) {
  const visual = lightVisual(device.state)
  const anchor = ANCHORS.light
  const [x, , z] = anchor.base
  const level = useRef(visual.level)
  const light = useRef()
  const bulb = useRef()
  const halo = useRef()
  const pool = useRef()
  useInvalidateOn(visual.level)

  useFrame((_, delta) => {
    // Smoothly approach the backend-derived level (instant with reduced motion).
    level.current = reducedMotion ? visual.level : approach(level.current, visual.level, 5, Math.min(delta, 0.1))
    const l = level.current
    if (light.current) light.current.intensity = l * LIGHT_MAX_POINT_INTENSITY
    if (bulb.current) bulb.current.emissiveIntensity = l > 0.002 ? 0.4 + l * 3.6 : 0
    if (halo.current) {
      halo.current.material.opacity = l * 0.95
      halo.current.scale.setScalar(0.35 + l * 1.25)
    }
    if (pool.current) pool.current.opacity = l * 0.75
  })

  return (
    <DeviceShell device={device} anchor={anchor} reducedMotion={reducedMotion} {...shell}>
      <group position={[x, 0, z]}>
        <mesh position={[0, 0.03, 0]}>
          <cylinderGeometry args={[0.24, 0.26, 0.06, 24]} />
          <meshStandardMaterial color="#334155" metalness={0.6} roughness={0.35} />
        </mesh>
        <mesh position={[0, 0.85, 0]}>
          <cylinderGeometry args={[0.025, 0.025, 1.6, 8]} />
          <meshStandardMaterial color="#64748b" metalness={0.7} roughness={0.3} />
        </mesh>
        <mesh position={[0, 1.78, 0]}>
          <cylinderGeometry args={[0.13, 0.32, 0.34, 24, 1, true]} />
          <meshStandardMaterial color="#cbd5e1" roughness={0.6} side={2} emissive={COLORS.warmLight} emissiveIntensity={visual.level * 0.35} />
        </mesh>
        <mesh position={[0, 1.7, 0]}>
          <sphereGeometry args={[0.1, 16, 16]} />
          <meshStandardMaterial ref={bulb} color="#fde68a" emissive={COLORS.warmLight} emissiveIntensity={0} toneMapped={false} />
        </mesh>
        <Halo ref={halo} position={[0, 1.66, 0]} color={COLORS.warmLight} opacity={0} />
        <pointLight ref={light} position={[0, 1.6, 0]} color={COLORS.warmLight} intensity={0} distance={10} decay={1.5} />
        <FloorGlow ref={pool} position={[0, 0.02, -0.6]} size={5.5} color={COLORS.warmLight} opacity={0} />
      </group>
    </DeviceShell>
  )
}
