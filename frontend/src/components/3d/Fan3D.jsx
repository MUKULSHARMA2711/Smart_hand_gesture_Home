import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { DeviceShell, useInvalidateOn } from './DeviceShell'
import { ANCHORS } from './layout'
import { COLORS } from './palette'
import { approach, fanVisual } from './visualState'

const BLADES = [0, 1, 2]

/** Pedestal fan. Blade speed follows backend speed with smooth spin-up and spin-down. */
export function Fan3D({ device, reducedMotion, ...shell }) {
  const visual = fanVisual(device.state)
  const anchor = ANCHORS.fan
  const [x, , z] = anchor.base
  const yaw = Math.atan2(-2 - x, 0.5 - z) // face the middle of the living room
  const rotor = useRef()
  const blur = useRef()
  const velocity = useRef(visual.angularVelocity)
  useInvalidateOn(visual.angularVelocity)

  useFrame((_, delta) => {
    const dt = Math.min(delta, 0.1)
    if (reducedMotion) {
      velocity.current = 0 // no continuous motion; speed is shown on the label instead
    } else {
      velocity.current = approach(velocity.current, visual.angularVelocity, 1.6, dt)
    }
    if (rotor.current) rotor.current.rotation.z += velocity.current * dt
    if (blur.current) blur.current.opacity = Math.min(0.28, velocity.current / 60)
  })

  return (
    <DeviceShell device={device} anchor={anchor} reducedMotion={reducedMotion} {...shell}>
      <group position={[x, 0, z]} rotation-y={yaw}>
        <mesh position={[0, 0.03, 0]}>
          <cylinderGeometry args={[0.3, 0.34, 0.06, 24]} />
          <meshStandardMaterial color="#334155" metalness={0.6} roughness={0.35} />
        </mesh>
        <mesh position={[0, 0.65, 0]}>
          <cylinderGeometry args={[0.03, 0.035, 1.25, 8]} />
          <meshStandardMaterial color="#64748b" metalness={0.7} roughness={0.3} />
        </mesh>
        <group position={[0, 1.3, 0]}>
          <mesh position={[0, 0, -0.12]} rotation-x={Math.PI / 2}>
            <cylinderGeometry args={[0.11, 0.13, 0.22, 16]} />
            <meshStandardMaterial color="#475569" metalness={0.5} roughness={0.4} />
          </mesh>
          <mesh>
            <torusGeometry args={[0.5, 0.014, 8, 48]} />
            <meshStandardMaterial color="#94a3b8" metalness={0.6} roughness={0.3} emissive={COLORS.system} emissiveIntensity={visual.multiplier * 0.8} />
          </mesh>
          <group ref={rotor}>
            <mesh>
              <sphereGeometry args={[0.07, 12, 12]} />
              <meshStandardMaterial color="#cbd5e1" metalness={0.5} roughness={0.3} />
            </mesh>
            {BLADES.map((i) => (
              <mesh key={i} rotation-z={(i * 2 * Math.PI) / 3}>
                <boxGeometry args={[0.1, 0.44, 0.012]} />
                <meshStandardMaterial
                  color="#cbd5e1"
                  roughness={0.4}
                  emissive={COLORS.system}
                  emissiveIntensity={visual.multiplier * 0.5}
                />
              </mesh>
            ))}
          </group>
          <mesh position={[0, 0, 0.01]}>
            <circleGeometry args={[0.47, 32]} />
            <meshBasicMaterial ref={blur} color="#bae6fd" transparent opacity={0} depthWrite={false} />
          </mesh>
        </group>
      </group>
    </DeviceShell>
  )
}
