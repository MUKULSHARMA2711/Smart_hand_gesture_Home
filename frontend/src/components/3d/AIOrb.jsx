import { useEffect, useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { useInvalidateOn } from './DeviceShell'
import { Halo } from './glow'
import { SceneHtml } from './SceneHtml'
import { orbAppearance } from './visualState'

const RING_TILTS = [
  [Math.PI / 2, 0, 0],
  [Math.PI / 2.6, 0.5, 0],
  [Math.PI / 1.7, -0.6, 0.3],
]
const PARTICLES = 36

function OrbParticles({ color, speed }) {
  const mesh = useRef()
  const dummy = useMemo(() => new THREE.Object3D(), [])
  const seeds = useMemo(
    () => Array.from({ length: PARTICLES }, (_, i) => ({ radius: 0.9 + ((i * 7) % 11) * 0.06, tilt: (i * 0.618) % Math.PI, phase: i * 0.37 })),
    [],
  )
  useFrame(({ clock }) => {
    if (!mesh.current) return
    const t = clock.elapsedTime * speed
    seeds.forEach(({ radius, tilt, phase }, i) => {
      const a = t + phase
      dummy.position.set(Math.cos(a) * radius, Math.sin(a) * radius * Math.cos(tilt), Math.sin(a) * radius * Math.sin(tilt))
      dummy.updateMatrix()
      mesh.current.setMatrixAt(i, dummy.matrix)
    })
    mesh.current.instanceMatrix.needsUpdate = true
  })
  return (
    <instancedMesh ref={mesh} args={[undefined, undefined, PARTICLES]} frustumCulled={false}>
      <sphereGeometry args={[0.025, 6, 6]} />
      <meshBasicMaterial color={color} transparent opacity={0.9} blending={THREE.AdditiveBlending} depthWrite={false} toneMapped={false} />
    </instancedMesh>
  )
}

/**
 * The AI core. `state` is one of idle, listening, thinking, planning, executing,
 * success, error, and comes from the real assistant lifecycle.
 */
export function AIOrb({ state = 'idle', position = [0, 0, 0], reducedMotion = false, showLabel = true }) {
  const look = orbAppearance(state)
  const core = useRef()
  const coreMaterial = useRef()
  const rings = useRef([])
  const shell = useRef()
  const halo = useRef()
  const waves = useRef([])
  const burst = useRef()
  const group = useRef()
  const changedAt = useRef(0)
  const color = useMemo(() => new THREE.Color(look.color), [look.color])
  useInvalidateOn(state)

  useEffect(() => {
    changedAt.current = performance.now()
  }, [state])

  useFrame(({ clock }, delta) => {
    const t = clock.elapsedTime
    const sinceChange = (performance.now() - changedAt.current) / 1000
    const pulse = reducedMotion ? 1 : 1 + look.pulseAmount * Math.sin(t * look.pulseSpeed)

    if (core.current) core.current.scale.setScalar(pulse)
    if (coreMaterial.current) {
      coreMaterial.current.emissive.lerp(color, 0.12)
      coreMaterial.current.emissiveIntensity = 1.6 + look.glow * 1.6 * pulse
    }
    if (halo.current) {
      halo.current.material.color.lerp(color, 0.12)
      halo.current.scale.setScalar(2.4 * (0.8 + look.glow * 0.4) * pulse)
    }
    rings.current.forEach((ring, i) => {
      if (!ring) return
      ring.visible = i < look.rings
      ring.material.color.lerp(color, 0.12)
      if (!reducedMotion) ring.rotation.z += delta * look.ringSpeed * (i % 2 ? -1 : 1) * (1 + i * 0.3)
    })
    if (shell.current) {
      shell.current.visible = look.shell
      if (!reducedMotion) {
        shell.current.rotation.y += delta * 0.6
        shell.current.rotation.x += delta * 0.25
      }
    }
    waves.current.forEach((wave, i) => {
      if (!wave) return
      wave.visible = look.waves && !reducedMotion
      const phase = (t * 0.6 + i * 0.5) % 1
      wave.scale.setScalar(1 + phase * 1.6)
      wave.material.opacity = (1 - phase) * 0.45
    })
    if (burst.current) {
      const p = Math.min(1, sinceChange / 0.9)
      burst.current.visible = Boolean(look.burst) && p < 1 && !reducedMotion
      burst.current.scale.setScalar(1 + p * 3)
      burst.current.material.opacity = (1 - p) * 0.8
      burst.current.material.color.copy(color)
    }
    if (group.current) {
      group.current.position.x = look.shake && sinceChange < 0.6 && !reducedMotion ? position[0] + Math.sin(t * 60) * 0.04 : position[0]
    }
  })

  return (
    <group ref={group} position={position}>
      {/* Projection cone towards the house */}
      <mesh position={[0, -1.9, 0]}>
        <cylinderGeometry args={[0.12, 1.7, 3.2, 32, 1, true]} />
        <meshBasicMaterial color={look.color} transparent opacity={0.045} side={THREE.DoubleSide} depthWrite={false} blending={THREE.AdditiveBlending} />
      </mesh>
      <mesh ref={core}>
        <sphereGeometry args={[0.42, 32, 32]} />
        <meshStandardMaterial ref={coreMaterial} color="#0b1324" emissive={look.color} emissiveIntensity={2} roughness={0.3} toneMapped={false} />
      </mesh>
      <Halo ref={halo} color={look.color} opacity={0.75} scale={2.4} />
      {RING_TILTS.map((rotation, i) => (
        <mesh key={i} ref={(el) => (rings.current[i] = el)} rotation={rotation}>
          <torusGeometry args={[0.7 + i * 0.2, 0.012, 8, 96]} />
          <meshBasicMaterial color={look.color} transparent opacity={0.8} toneMapped={false} />
        </mesh>
      ))}
      <mesh ref={shell} visible={look.shell}>
        <icosahedronGeometry args={[0.66, 1]} />
        <meshBasicMaterial color={look.color} wireframe transparent opacity={0.35} toneMapped={false} />
      </mesh>
      {[0, 1].map((i) => (
        <mesh key={i} ref={(el) => (waves.current[i] = el)} rotation-x={Math.PI / 2} visible={false}>
          <ringGeometry args={[0.55, 0.58, 64]} />
          <meshBasicMaterial color={look.color} transparent opacity={0} side={THREE.DoubleSide} depthWrite={false} toneMapped={false} />
        </mesh>
      ))}
      <mesh ref={burst} rotation-x={Math.PI / 2} visible={false}>
        <ringGeometry args={[0.5, 0.56, 64]} />
        <meshBasicMaterial color={look.color} transparent opacity={0} side={THREE.DoubleSide} depthWrite={false} toneMapped={false} />
      </mesh>
      {look.particles && !reducedMotion && <OrbParticles color={look.color} speed={state === 'executing' ? 2.4 : 1.4} />}
      {showLabel && (
        <SceneHtml position={[0, -0.95, 0]} center style={{ pointerEvents: 'none' }} zIndexRange={[20, 0]}>
          <div className={`scene-orb-label scene-orb-label--${state}`}>AI core · {state}</div>
        </SceneHtml>
      )}
    </group>
  )
}
