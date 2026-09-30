// 用 Python 独立算出的参考值核对统计逻辑。运行：npm test
import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { prepare, rangeStart, zodiacStats } from './stats.js'
import { backtest } from './backtest.js'
import { numbersOf, PROB } from './zodiac.js'

const raw = JSON.parse(fs.readFileSync(new URL('../../../data/draws.json', import.meta.url)))
const draws = prepare(raw)
// 参考值按 2026-09-29 第272期时的数据算出，数据每天更新后仍用这一段来核对
const snapshot = prepare(raw.filter((d) => d.date <= '2026-09-29'))

test('本命年号码', () => {
  assert.deepEqual(numbersOf('马', '马'), [1, 13, 25, 37, 49])
  assert.deepEqual(numbersOf('蛇', '马'), [2, 14, 26, 38])
  assert.deepEqual(numbersOf('虎', '马'), [5, 17, 29, 41])
  assert.equal(PROB.平码(4).toFixed(4), '0.4717')
  assert.equal(PROB.平码(5).toFixed(4), '0.5539')
})

test('本命在春节当天切换', () => {
  const switches = draws.filter((d, i) => i === 0 || d.bm !== draws[i - 1].bm).map((d) => `${d.date} ${d.bm}`)
  assert.deepEqual(switches, [
    '2020-03-07 鼠', '2021-02-12 牛', '2022-02-01 虎', '2023-01-22 兔',
    '2024-02-10 龙', '2025-01-29 蛇', '2026-02-17 马',
  ])
})

// [号码范围, 时间范围, 生肖, 当前未出, 平均间隔, 最长未出, 出现次数] —— 数据截至 2026-09-29 第272期
const REF = [
  ['特码', '全部', '虎', 33, 10.809, 70, 200],
  ['特码', '全部', '马', 7, 11.3646, 72, 193],
  ['特码', '今年', '虎', 33, 9.12, 33, 25],
  ['特码', '今年', '狗', 8, 14.2222, 42, 18],
  ['平码', '全部', '狗', 4, 1.1489, 17, 1109],
  ['平码', '今年', '马', 1, 0.8013, 7, 151],
]
test('未出与出现次数与 Python 参考值一致', () => {
  for (const [scope, range, z, cur, avg, max, count] of REF) {
    const row = zodiacStats(snapshot, scope, rangeStart(snapshot, range)).find((r) => r.z === z)
    assert.equal(row.cur, cur, `${scope}${range}${z} 当前未出`)
    assert.equal(row.avgGap.toFixed(4), avg.toFixed(4), `${scope}${range}${z} 平均间隔`)
    assert.equal(row.maxGap, max, `${scope}${range}${z} 最长未出`)
    assert.equal(row.count, count, `${scope}${range}${z} 出现次数`)
  }
  const bt = backtest(snapshot, '特码', 0, '最久未出', 3, 30)
  assert.equal(bt.rounds, 2386)
  assert.equal(bt.hits, 610)
})

test('理论次数之和：特码每期恰好 1 个生肖', () => {
  const rows = zodiacStats(draws, '特码', 0)
  const exp = rows.reduce((s, r) => s + r.expected, 0)
  assert.ok(Math.abs(exp - draws.length) < 1e-6)
  assert.equal(rows.reduce((s, r) => s + r.count, 0), draws.length)
})
