import { Block } from './LivingRoom'
import { COLORS } from './palette'

export function Bedroom() {
  return (
    <group>
      {/* Bed with its headboard against the back wall, under the AC */}
      <Block args={[2.0, 0.3, 2.2]} position={[3.7, 0.16, -2.2]} />
      <Block args={[1.9, 0.18, 2.05]} position={[3.7, 0.4, -2.15]} color={COLORS.furnitureLight} />
      <Block args={[2.05, 0.85, 0.12]} position={[3.7, 0.43, -3.36]} />
      <Block args={[1.5, 0.12, 0.42]} position={[3.7, 0.55, -2.95]} color="#3a4c73" />
      {/* Nightstand */}
      <Block args={[0.48, 0.46, 0.42]} position={[1.6, 0.23, -3.1]} />
    </group>
  )
}
