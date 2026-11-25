import { test } from 'node:test'
import assert from 'node:assert/strict'
import { scoreToUnits, issueForDate, totals } from './ledger.js'

test('积分按百分之一单位保存，既有数值和输赢统计不变', () => {
  assert.equal(scoreToUnits('0.29', 'win'), 29)
  assert.equal(scoreToUnits('150.01', 'loss'), -15001)
  assert.deepEqual(totals([{ amount_cents: 15000 }, { amount_cents: -12000 }, { amount_cents: 5000 }]), { win: 20000, loss: 12000, net: 8000 })
  for (const value of ['0', '-1', '1.001', '1e3', 'NaN', '1000000.01']) assert.throws(() => scoreToUnits(value, 'win'))
})
test('期数默认值正确处理闰年和跨年', () => {
  assert.equal(issueForDate('2026-11-25'), 329)
  assert.equal(issueForDate('2024-12-31'), 366)
  assert.equal(issueForDate('2027-01-01'), 1)
})
