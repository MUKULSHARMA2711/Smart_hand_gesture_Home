import { Edges } from '@react-three/drei'
import { Bedroom } from './Bedroom'
import { DOOR, HOUSE, ROOMS } from './layout'
import { Entrance } from './Entrance'
import { LivingRoom } from './LivingRoom'
import { COLORS } from './palette'
import { SceneHtml } from './SceneHtml'

/** A wall segment between two floor points. */
function Wall({ from, to, height = HOUSE.wallHeight, opacity = 0.82 }) {
  const [x1, z1] = from
  const [x2, z2] = to
  const length = Math.hypot(x2 - x1, z2 - z1)
  const angle = Math.atan2(z2 - z1, x2 - x1)
  return (
    <mesh position={[(x1 + x2) / 2, height / 2, (z1 + z2) / 2]} rotation-y={-angle}>
      <boxGeometry args={[length, height, HOUSE.thickness]} />
      <meshStandardMaterial color={COLORS.wall} roughness={0.85} metalness={0.1} transparent opacity={opacity} />
      <Edges color={COLORS.wallEdge} />
    </mesh>
  )
}

function RoomFloor({ room, showLabel }) {
  const [x1, x2] = room.x
  const [z1, z2] = room.z
  return (
    <group>
      <mesh position={[(x1 + x2) / 2, 0.005, (z1 + z2) / 2]} rotation-x={-Math.PI / 2}>
        <planeGeometry args={[x2 - x1 - 0.04, z2 - z1 - 0.04]} />
        <meshStandardMaterial color={room.floor} roughness={0.95} />
      </mesh>
      {showLabel && (
        <SceneHtml position={[room.labelAt[0], 0.02, room.labelAt[1]]} style={{ pointerEvents: 'none' }} zIndexRange={[10, 0]}>
          <span className="scene-room-label">{room.label}</span>
        </SceneHtml>
      )}
    </group>
  )
}

export function HouseModel({ showLabels = true }) {
  const { minX, maxX, minZ, maxZ, lowWall } = HOUSE
  const doorEnd = DOOR.hingeX + DOOR.width + 0.05
  return (
    <group>
      {/* Foundation slab */}
      <mesh position={[0, -0.1, 0]}>
        <boxGeometry args={[maxX - minX + 0.4, 0.2, maxZ - minZ + 0.4]} />
        <meshStandardMaterial color="#0a1222" roughness={0.9} />
        <Edges color={COLORS.wallEdge} />
      </mesh>
      {ROOMS.map((room) => (
        <RoomFloor key={room.id} room={room} showLabel={showLabels} />
      ))}

      {/* Full-height back and left walls */}
      <Wall from={[minX, minZ]} to={[maxX, minZ]} />
      <Wall from={[minX, minZ]} to={[minX, maxZ]} />
      {/* Interior partitions (with doorways) */}
      <Wall from={[1, minZ]} to={[1, -0.25]} />
      <Wall from={[1, 0.9]} to={[3.9, 0.9]} />
      {/* Cut-away front and right walls */}
      <Wall from={[minX, maxZ]} to={[DOOR.hingeX - 0.05, maxZ]} height={lowWall} />
      <Wall from={[doorEnd, maxZ]} to={[maxX, maxZ]} height={lowWall} />
      <Wall from={[maxX, minZ]} to={[maxX, maxZ]} height={lowWall} />

      <LivingRoom />
      <Bedroom />
      <Entrance />
    </group>
  )
}
