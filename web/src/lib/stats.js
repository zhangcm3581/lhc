// 所有统计都在浏览器里现算：2400 期左右的数据，全部指标算一遍只要几毫秒。
import { ZODIACS, SCOPES, PROB, benmingOf, numbersOf, zIndex } from './zodiac.js'

const WINDOWS = [10, 30, 50, 100]

export function prepare(raw) {
  const draws = raw
    .map((d) => {
      return { ...d, year: Number(d.date.slice(0, 4)), bm: benmingOf(d.nums, d.zodiacs) }
    })
    .sort((a, b) => a.year - b.year || a.issue - b.issue)
  draws.forEach((d, i) => (d.idx = i))
  return draws
}

// 范围起点在全部数据里的下标。"今年"按公历年，与原站一致。
export function rangeStart(draws, range) {
  if (range === '全部') return 0
  const y = draws.at(-1).year
  return draws.findIndex((d) => d.year === y)
}

const kOf = (z, d) => (z === d.bm ? 5 : 4)
const hitSets = (draws, scope) => draws.map((d) => new Set(SCOPES[scope](d)))

// 生肖总表：当前未出、平均间隔、最长未出、出现次数、理论次数、冷热、连出……
// 当前未出按全部历史算；平均间隔、最长未出等按所选范围算（只统计在范围内结束的间隔）。
export function zodiacStats(draws, scope, start) {
  const N = draws.length
  const rangeLen = N - start
  const prob = PROB[scope]
  const sets = hitSets(draws, scope)
  const latestBm = draws.at(-1).bm
  const acc = ZODIACS.map((z) => ({
    z, count: 0, expected: 0, variance: 0, gaps: [], last: -1, streak: 0, maxStreak: 0,
    recent: Object.fromEntries(WINDOWS.map((w) => [w, 0])),
  }))

  for (let i = 0; i < N; i++) {
    const inRange = i >= start
    for (const a of acc) {
      if (inRange) {
        const p = prob(kOf(a.z, draws[i]))
        a.expected += p
        a.variance += p * (1 - p)
      }
      if (!sets[i].has(a.z)) {
        a.streak = 0
        continue
      }
      if (inRange) {
        if (a.last >= 0) a.gaps.push({ len: i - a.last - 1, from: a.last + 1, to: i - 1 })
        a.count++
        a.streak++
        a.maxStreak = Math.max(a.maxStreak, a.streak)
        for (const w of WINDOWS) if (i >= N - Math.min(w, rangeLen)) a.recent[w]++
      }
      a.last = i
    }
  }

  return acc.map((a) => {
    const cur = N - 1 - a.last
    const lens = a.gaps.map((g) => g.len)
    const maxDone = lens.length ? Math.max(...lens) : 0
    const avgGap = lens.length ? lens.reduce((s, x) => s + x, 0) / lens.length : null
    const p = prob(kOf(a.z, draws.at(-1)))
    const zscore = a.variance ? (a.count - a.expected) / Math.sqrt(a.variance) : 0
    return {
      z: a.z,
      isBenming: a.z === latestBm,
      numbers: numbersOf(a.z, latestBm),
      cur,
      avgGap,
      theoryGap: (1 - p) / p,
      maxGap: Math.max(maxDone, cur),
      atMax: cur > 0 && cur >= maxDone,
      times: avgGap ? cur / avgGap : null,
      count: a.count,
      expected: a.expected,
      diff: a.count - a.expected,
      zscore,
      heat: zscore >= 1 ? '热' : zscore <= -1 ? '冷' : '温',
      recent: a.recent,
      streak: a.streak,
      maxStreak: a.maxStreak,
      gaps: a.gaps,
    }
  })
}

// 间隔分布：每两次开出之间隔了多少期。cur 是当前未出，保证横轴能覆盖到它
export function gapHistogram(gaps, cur = 0) {
  const lens = gaps.map((g) => g.len)
  const max = Math.max(cur, ...lens)
  const width = max <= 20 ? 1 : 5
  const bins = Array.from({ length: Math.floor(max / width) + 1 }, (_, b) => ({
    label: width === 1 ? `${b * width}` : `${b * width}-${b * width + width - 1}`,
    count: 0,
  }))
  for (const x of lens) bins[Math.floor(x / width)].count++
  return { bins, curBin: bins[Math.floor(cur / width)].label }
}

// 下期再出：某生肖开出后，下一期又开出的比例（theory 为理论值）
export function reappear(draws, scope, start) {
  const sets = hitSets(draws, scope)
  const prob = PROB[scope]
  const rate = (num, exp, den) => ({ den, num, exp, rate: den ? num / den : null, theory: den ? exp / den : null })
  const rows = ZODIACS.map((z) => {
    let den = 0, num = 0, exp = 0
    for (let i = start; i + 1 < draws.length; i++) {
      if (!sets[i].has(z)) continue
      den++
      num += sets[i + 1].has(z)
      exp += prob(kOf(z, draws[i + 1]))
    }
    return { z, ...rate(num, exp, den) }
  })
  const sum = (f) => rows.reduce((s, r) => s + r[f], 0)
  return { rows, total: rate(sum('num'), sum('exp'), sum('den')) }
}

// 单期结构：每期 7 个号涉及几个生肖
export function drawStructure(draws, start) {
  const distinct = { 3: 0, 4: 0, 5: 0, 6: 0, 7: 0 }
  const list = draws.slice(start)
  for (const d of list) {
    const kinds = new Set(d.zodiacs).size
    distinct[kinds] = (distinct[kinds] || 0) + 1
  }
  return { n: list.length, distinct }
}
