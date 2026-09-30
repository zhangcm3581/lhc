// 规则回测：每期开奖前只用之前的数据按规则选生肖，再看这一期中没中。
// 同时用"随机选同样个数"重复多次作对照，判断规则是否比随机更好。
import { ZODIACS, SCOPES, zIndex } from './zodiac.js'

export const RULES = {
  最久未出: { usesK: true, usesWindow: false },
  近期最热: { usesK: true, usesWindow: true },
  近期最冷: { usesK: true, usesWindow: true },
  只选本命: { usesK: false, usesWindow: false },
  上期特码生肖: { usesK: false, usesWindow: false },
}

const byScore = (score) => (a, b) => score(b) - score(a) || zIndex(a) - zIndex(b)

// 第 i 期开奖前，规则选出的生肖（只用第 i 期之前的数据）
function makePicker(draws, scope, rule, K, window) {
  const sets = draws.map((d) => new Set(SCOPES[scope](d)))
  const last = Object.fromEntries(ZODIACS.map((z) => [z, -1]))
  const inWindow = Object.fromEntries(ZODIACS.map((z) => [z, 0]))
  let seen = 0
  return {
    pick(i) {
      const bm = i < draws.length ? draws[i].bm : draws.at(-1).bm
      switch (rule) {
        case '最久未出': return [...ZODIACS].sort(byScore((z) => i - last[z])).slice(0, K)
        case '近期最热': return [...ZODIACS].sort(byScore((z) => inWindow[z])).slice(0, K)
        case '近期最冷': return [...ZODIACS].sort(byScore((z) => -inWindow[z])).slice(0, K)
        case '只选本命': return [bm]
        case '上期特码生肖': return i > 0 ? [draws[i - 1].zodiacs[6]] : []
      }
    },
    // 把第 i 期开奖计入状态
    advance(i) {
      for (const z of sets[i]) { last[z] = i; inWindow[z]++ }
      if (++seen > window) for (const z of sets[i - window]) inWindow[z]--
    },
    sets,
  }
}

function score(sets, start, picksAt) {
  let rounds = 0, picks = 0, hits = 0, anyHit = 0, missRun = 0, worstMiss = 0
  for (let i = start; i < sets.length; i++) {
    const p = picksAt(i)
    if (!p.length) continue
    const h = p.filter((z) => sets[i].has(z)).length
    rounds++
    picks += p.length
    hits += h
    if (h) { anyHit++; missRun = 0 } else worstMiss = Math.max(worstMiss, ++missRun)
  }
  return { rounds, picks, hits, hitRate: picks ? hits / picks : 0, anyRate: rounds ? anyHit / rounds : 0, worstMiss, currentMiss: missRun }
}

function mulberry32(seed) {
  return () => {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

export function backtest(draws, scope, start, rule, K, window, randomRuns = 200) {
  const size = RULES[rule].usesK ? K : 1
  const picker = makePicker(draws, scope, rule, size, window)
  const picked = []
  for (let i = 0; i < draws.length; i++) {
    picked[i] = picker.pick(i)
    picker.advance(i)
  }
  const first = Math.max(start, 1)
  const result = score(picker.sets, first, (i) => picked[i])

  const rand = mulberry32(20260930)
  const runs = []
  for (let r = 0; r < randomRuns; r++) {
    runs.push(score(picker.sets, first, () => {
      const pool = [...ZODIACS]
      for (let j = 0; j < size; j++) {
        const k = j + Math.floor(rand() * (12 - j))
        ;[pool[j], pool[k]] = [pool[k], pool[j]]
      }
      return pool.slice(0, size)
    }))
  }
  const avg = (f) => runs.reduce((s, x) => s + f(x), 0) / runs.length
  const random = { hitRate: avg((x) => x.hitRate), anyRate: avg((x) => x.anyRate), worstMiss: avg((x) => x.worstMiss) }
  // 规则比随机好的次数占比：随机 200 次里，有多少次命中率不如这条规则
  const beat = runs.filter((x) => x.hitRate < result.hitRate).length / runs.length

  return { ...result, size, random, beat, next: picker.pick(draws.length) }
}
