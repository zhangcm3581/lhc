<script setup>
import { computed } from 'vue'
import { drawStructure } from '../lib/stats.js'
import { pct } from '../lib/format.js'

const props = defineProps({ draws: Array, scope: String, range: String, start: Number })
const s = computed(() => drawStructure(props.draws, props.start))
const latest = computed(() => props.draws.at(-1))
const latestKinds = computed(() => new Set(latest.value.zodiacs).size)
const maxDistinct = computed(() => Math.max(...Object.values(s.value.distinct)))
</script>

<template>
  <section class="card">
    <div class="card-head">
      <h2 class="card-title">每期 7 个号涉及几个生肖</h2>
      <span class="card-meta">{{ range }}</span>
    </div>
    <p class="card-help">橙色：最新一期</p>
    <div class="bars">
      <div v-for="(n, k) in s.distinct" :key="k" class="bar-row" :class="{ now: Number(k) === latestKinds }">
        <span class="bar-label">{{ k }} 个生肖</span>
        <div class="bar-track"><div class="bar-fill" :style="{ width: (n / maxDistinct) * 100 + '%' }"></div></div>
        <span class="bar-value num">{{ n }} 期 · {{ pct(n / s.n) }}</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.bars { display: flex; flex-direction: column; gap: 12px; }
.bar-row { display: grid; grid-template-columns: 62px 1fr 104px; align-items: center; gap: 10px; }
.bar-label { color: var(--ink-2); font-size: 14px; }
.bar-track { height: 10px; background: var(--surface-2); border-radius: 5px; overflow: hidden; }
.bar-fill { height: 100%; background: var(--series); border-radius: 5px; }
.bar-value { font-size: 13px; color: var(--ink-2); text-align: right; font-variant-numeric: tabular-nums; }
.bar-row.now .bar-label { color: var(--accent); font-weight: 600; }
.bar-row.now .bar-fill { background: var(--accent); }
</style>
