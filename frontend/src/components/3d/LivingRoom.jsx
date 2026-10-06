import { RoundedBox } from '@react-three/drei'
import { COLORS } from './palette'

/** Furniture silhouettes only — the room is context for the devices, not a game level. */
function Block({ args, position, color = COLORS.furniture, radius = 0.05, emissive, emissiveIntensity = 0 }) {
  return (
    <RoundedBox args={args} radius={radius} smoothness={2} position={position}>
      <meshStandardMaterial
        color={color}
        roughness={0.8}
        emissive={emissive ?? '#000000'}
        emissiveIntensity={emissiveIntensity}
      />
    </RoundedBox>
  )
}

export function LivingRoom() {
  return (
    <group>
      {/* Rug */}
      <mesh position={[-2.2, 0.012, 0.9]} rotation-x={-Math.PI / 2}>
        <planeGeometry args={[3.3, 2.5]} />
        <meshStandardMaterial color="#17243f" roughness={1} />
      </mesh>
      {/* Sofa facing the TV wall */}
      <Block args={[2.6, 0.36, 0.9]} position={[-2.2, 0.2, 2.2]} />
      <Block args={[2.6, 0.55, 0.22]} position={[-2.2, 0.5, 2.6]} />
      <Block args={[0.22, 0.5, 0.9]} position={[-3.45, 0.3, 2.2]} />
      <Block args={[0.22, 0.5, 0.9]} position={[-0.95, 0.3, 2.2]} />
      {/* Coffee table */}
      <Block args={[1.3, 0.1, 0.65]} position={[-2.2, 0.38, 0.9]} color={COLORS.furnitureLight} radius={0.03} />
      <Block args={[1.1, 0.32, 0.45]} position={[-2.2, 0.17, 0.9]} />
      {/* TV console and screen */}
      <Block args={[2.3, 0.42, 0.42]} position={[-2.2, 0.22, -3.15]} />
      <Block
        args={[1.9, 1.05, 0.06]}
        position={[-2.2, 1.25, -3.4]}
        color="#0b1526"
        radius={0.02}
        emissive="#0b2a4a"
        emissiveIntensity={0.6}
      />
    </group>
  )
}

export { Block }
