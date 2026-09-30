<script setup>
import { computed } from 'vue'
import { zodiacStats, reappear } from '../lib/stats.js'
import { pct } from '../lib/format.js'

const props = defineProps({ draws: Array, scope: String, range: String, start: Number })
const rows = computed(() => zodiacStats(props.draws, props.scope, props.start))
const re = computed(() => reappear(props.draws, props.scope, props.start))
const bm = computed(() => props.draws.at(-1).bm)
const cmp = (k) => (k.rate == null ? '' : k.rate > k.theory ? 'pos' : 'neg')
</script>

<template>
  <section class="card">
    <div class="card-head">
      <h2 class="card-title">连出与再次出现</h2>
      <span class="card-meta">{{ range }}</span>
    </div>
    <p class="card-help">下期再出：这个生肖开出后，下一期又开出的比例 · <span class="pos">红色</span>高于理论值，<span class="neg">蓝色</span>低于理论值</p>
    <div class="scroll-x">
      <table class="data">
        <thead>
          <tr><th>生肖</th><th>当前连出</th><th>最长连出</th><th>下期再出</th><th>理论值</th></tr>
        </thead>
        <tbody>
          <tr v-for="(r, i) in re.rows" :key="r.z">
            <td><b>{{ r.z }}</b> <span v-if="r.z === bm" class="tag tag-accent">本命</span></td>
            <td>{{ rows[i].streak }}</td>
            <td>{{ rows[i].maxStreak }}</td>
            <td :class="cmp(r)">{{ pct(r.rate) }}</td>
            <td class="muted">{{ pct(r.theory) }}</td>
          </tr>
          <tr class="total">
            <td>合计</td><td></td><td></td>
            <td :class="cmp(re.total)">{{ pct(re.total.rate) }}</td>
            <td class="muted">{{ pct(re.total.theory) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.total td { font-weight: 600; }
</style>
