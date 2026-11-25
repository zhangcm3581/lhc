import { test } from 'node:test'
import assert from 'node:assert/strict'
import { amountInCents, issueForDate, totals } from './ledger.js'

test('金额按分保存，输赢统计准确', () => {
  assert.equal(amountInCents('0.29', 'win'), 29)
  assert.equal(amountInCents('150.01', 'loss'), -15001)
  assert.deepEqual(totals([{ amount_cents: 15000 }, { amount_cents: -12000 }, { amount_cents: 5000 }]), { win: 20000, loss: 12000, net: 8000 })
  for (const value of ['0', '-1', '1.001', '1e3', 'NaN', '1000000.01']) assert.throws(() => amountInCents(value, 'win'))
})
test('期数默认值正确处理闰年和跨年', () => {
  assert.equal(issueForDate('2026-11-25'), 329)
  assert.equal(issueForDate('2024-12-31'), 366)
  assert.equal(issueForDate('2027-01-01'), 1)
})
