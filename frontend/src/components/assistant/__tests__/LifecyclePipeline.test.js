import { describe, expect, it } from 'vitest'
import { stageStatus } from '../LifecyclePipeline'

const STAGES = ['request', 'understanding', 'context', 'plan', 'validation', 'execution', 'result']
const statuses = (phase) => STAGES.map((stage) => stageStatus(stage, phase))

describe('request lifecycle stages', () => {
  it('waits on understanding while the backend is thinking', () => {
    expect(statuses('thinking')).toEqual(['done', 'active', 'idle', 'idle', 'idle', 'idle', 'idle'])
  })

  it('reveals the plan, then execution, then the result', () => {
    expect(statuses('planning')).toEqual(['done', 'done', 'done', 'active', 'idle', 'idle', 'idle'])
    expect(statuses('executing')).toEqual(['done', 'done', 'done', 'done', 'done', 'active', 'idle'])
    expect(statuses('success')).toEqual(Array(7).fill('done'))
    expect(statuses('error')).toEqual(Array(7).fill('done'))
  })
})
