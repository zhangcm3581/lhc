<script setup>
import { computed } from 'vue'
import { zodiacStats } from '../lib/stats.js'
import { PROB, SCOPES } from '../lib/zodiac.js'
import { pct, fix, signed } from '../lib/format.js'
import Ball from '../components/Ball.vue'
import { SHOW_SPECIAL } from '../lib/config.js'

const props = defineProps({ draws: Array, scope: String, range: String, start: Number })
const latest = computed(() => props.draws.at(-1))
const bm = computed(() => latest.value.bm)
const rows = computed(() => zodiacStats(props.draws, props.scope, props.start))
const rowOf = (z) => rows.value.find((r) => r.z === z)

// 本命按每期当时的本命计算：当前连续几期本命没出
const bmMiss = computed(() => {
  let n = 0
  for (let i = props.draws.length - 1; i >= 0; i--) {
    const d = props.draws[i]
    if (SCOPES[props.scope](d).includes(d.bm)) break
    n++
  }
  return n
})
</script>

<template>
  <section class="card">
    <div class="card-head">
      <h2 class="card-title">本命生肖「{{ bm }}」</h2>
      <span class="card-meta">{{ latest.year }} {{ bm }}年 · 每年春节切换</span>
    </div>
    <div class="bm-line">
      <span class="bm-avatar">{{ bm }}</span>
      <div class="bm-balls"><Ball v-for="n in [1, 13, 25, 37, 49]" :key="n" :n="n" /></div>
    </div>
    <div class="grid-tiles">
      <div class="tile">
        <div class="tile-label">本命 · 5 个号</div>
        <div class="tile-value">{{ pct(PROB.平码(5)) }}</div>
        <div class="tile-sub">每期出现的理论概率<template v-if="SHOW_SPECIAL"> · 特码 {{ pct(PROB.特码(5)) }}</template></div>
      </div>
      <div class="tile">
        <div class="tile-label">其他生肖 · 4 个号</div>
        <div class="tile-value">{{ pct(PROB.平码(4)) }}</div>
        <div class="tile-sub">每期出现的理论概率<template v-if="SHOW_SPECIAL"> · 特码 {{ pct(PROB.特码(4)) }}</template></div>
      </div>
    </div>
  </section>

  <section class="card">
    <div class="card-head">
      <h2 class="card-title">本命追踪</h2>
      <span class="card-meta">{{ range }}</span>
    </div>
    <div class="grid-tiles">
      <div class="tile">
        <div class="tile-label">本命当前未出</div>
        <div v-if="bmMiss === 0" class="tile-value fresh">最新一期开出</div>
        <div v-else class="tile-value">{{ bmMiss }}<span class="unit">期</span></div>
        <div class="tile-sub">平均间隔 {{ fix(rowOf(bm).avgGap) }} 期 · 最长 {{ rowOf(bm).maxGap }} 期</div>
      </div>
      <div class="tile">
        <div class="tile-label">「{{ bm }}」出现次数</div>
        <div class="tile-value">{{ rowOf(bm).count }}</div>
        <div class="tile-sub">理论 {{ fix(rowOf(bm).expected) }} · 偏差 {{ signed(rowOf(bm).diff) }}</div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.bm-line { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.bm-avatar {
  flex: none; width: 44px; height: 44px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;
  background: var(--accent); color: #fff; font-size: 22px; font-weight: 700;
}
.bm-balls { display: flex; gap: 6px; flex-wrap: wrap; }
</style>
