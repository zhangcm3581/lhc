<script setup>
import { ref, computed } from 'vue'
import { zodiacStats, gapHistogram } from '../lib/stats.js'
import { fix } from '../lib/format.js'
import ZodiacPicker from '../components/ZodiacPicker.vue'
import EChart from '../components/EChart.vue'

const props = defineProps({ draws: Array, scope: String, range: String, start: Number })
const rows = computed(() => zodiacStats(props.draws, props.scope, props.start))
// 默认选当前未出最久的生肖
const picked = ref([...zodiacStats(props.draws, props.scope, props.start)].sort((a, b) => b.cur - a.cur)[0].z)
const row = computed(() => rows.value.find((r) => r.z === picked.value))
const N = computed(() => props.draws.length)

const hist = computed(() => gapHistogram(row.value.gaps, row.value.cur))

// 最长的几次未出（含正在进行的这次）
const longest = computed(() => {
  const list = row.value.gaps.map((g) => ({ ...g, ongoing: false }))
  if (row.value.cur > 0) list.push({ len: row.value.cur, from: N.value - row.value.cur, to: N.value - 1, ongoing: true })
  return list.sort((a, b) => b.len - a.len).slice(0, 5)
})
const at = (i) => props.draws[i]

const option = computed(() => (t) => ({
  grid: { left: 8, right: 8, top: 16, bottom: 4, containLabel: true },
  tooltip: {
    ...t.tooltip,
    trigger: 'axis',
    axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(128,128,128,0.08)' } },
    formatter: (p) => `间隔 ${p[0].name} 期：${p[0].value} 次`,
  },
  xAxis: { type: 'category', data: hist.value.bins.map((b) => b.label), ...t.axis, splitLine: { show: false } },
  yAxis: { type: 'value', ...t.axis, minInterval: 1 },
  series: [
    {
      type: 'bar',
      barCategoryGap: 2,
      itemStyle: { color: t.series, borderRadius: [4, 4, 0, 0] },
      data: hist.value.bins.map((b) => b.count),
      markLine: {
        silent: true,
        symbol: 'none',
        lineStyle: { color: t.accent, type: 'solid', width: 2 },
        label: { formatter: `当前 ${row.value.cur} 期`, color: t.accent, position: 'end' },
        data: [{ xAxis: hist.value.curBin }],
      },
    },
  ],
}))
</script>

<template>
  <section class="card">
    <div class="card-head">
      <h2 class="card-title">未出分析</h2>
      <span class="card-meta">{{ range }}</span>
    </div>
    <ZodiacPicker v-model="picked" :benming="draws.at(-1).bm" />
    <div class="grid-tiles two stats">
      <div class="tile">
        <div class="tile-label">当前未出</div>
        <div v-if="row.cur === 0" class="tile-value fresh">最新一期开出</div>
        <div v-else class="tile-value">{{ row.cur }}<span class="unit">期</span></div>
        <div class="tile-sub">上次 {{ at(N - 1 - row.cur).date.slice(5) }} 第{{ at(N - 1 - row.cur).issue }}期</div>
      </div>
      <div class="tile">
        <div class="tile-label">平均间隔</div>
        <div class="tile-value">{{ fix(row.avgGap) }}<span class="unit">期</span></div>
        <div class="tile-sub">理论 {{ fix(row.theoryGap) }} 期</div>
      </div>
      <div class="tile">
        <div class="tile-label">最长未出</div>
        <div class="tile-value">{{ row.maxGap }}<span class="unit">期</span></div>
        <div class="tile-sub">{{ range === '全部' ? '全部历史' : '今年' }}内</div>
      </div>
      <div class="tile">
        <div class="tile-label">未出倍数</div>
        <div class="tile-value">{{ fix(row.times) }}<span class="unit">倍</span></div>
        <div class="tile-sub">当前未出 ÷ 平均间隔</div>
      </div>
    </div>
  </section>

  <section class="card">
    <div class="card-head">
      <h2 class="card-title">间隔分布 · {{ picked }}</h2>
      <span class="card-meta">{{ range }}</span>
    </div>
    <p class="card-help">横轴：间隔期数 · 纵轴：次数 · <span class="accent-text">橙线：当前</span></p>
    <EChart :option="option" :height="240" />
  </section>

  <section class="card">
    <div class="card-head">
      <h2 class="card-title">最长的 5 次未出 · {{ picked }}</h2>
      <span class="card-meta">{{ range }}</span>
    </div>
    <div class="scroll-x">
      <table class="data">
        <thead>
          <tr><th>未出期数</th><th>时间段</th></tr>
        </thead>
        <tbody>
          <tr v-for="g in longest" :key="g.from">
            <td>
              <b class="digits len">{{ g.len }}</b> 期
              <span v-if="g.ongoing" class="tag tag-hot">进行中</span>
            </td>
            <td>
              <div>{{ at(g.from).date }} ~ {{ g.ongoing ? '至今' : at(g.to).date.slice(at(g.to).year === at(g.from).year ? 5 : 0) }}</div>
              <div class="muted small">第{{ at(g.from).issue }}期 ~ {{ g.ongoing ? `第${draws.at(-1).issue}期` : `第${at(g.to).issue}期` }}</div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.accent-text { color: var(--accent); }
.stats { margin-top: 14px; }
.grid-tiles.two { grid-template-columns: 1fr 1fr; }
.len { font-size: 18px; }
</style>
