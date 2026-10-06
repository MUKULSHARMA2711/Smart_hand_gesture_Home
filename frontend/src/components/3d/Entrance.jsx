import { Block } from './LivingRoom'

export function Entrance() {
  return (
    <group>
      {/* Bench along the right wall */}
      <Block args={[0.42, 0.42, 1.4]} position={[4.55, 0.21, 2.2]} />
      {/* Planter */}
      <mesh position={[1.55, 0.2, 3.0]}>
        <cylinderGeometry args={[0.18, 0.14, 0.4, 16]} />
        <meshStandardMaterial color="#26324d" roughness={0.8} />
      </mesh>
      <mesh position={[1.55, 0.62, 3.0]}>
        <icosahedronGeometry args={[0.3, 0]} />
        <meshStandardMaterial color="#1f4d46" roughness={0.9} flatShading />
      </mesh>
    </group>
  )
}
