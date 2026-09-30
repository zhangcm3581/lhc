<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { ZODIACS, SCOPES } from '../lib/zodiac.js'
import { shortDate } from '../lib/format.js'
import Seg from '../components/Seg.vue'
import DrawBalls from '../components/DrawBalls.vue'
import { SHOW_SPECIAL } from '../lib/config.js'

const props = defineProps({ draws: Array, scope: String, range: String, start: Number })
const bm = computed(() => props.draws.at(-1).bm)

// 显示多少期：默认"全部"，即所选时间范围（今年/全部）内的所有期
const SIZES = [
  { value: 'all', label: '全部' },
  { value: 50, label: '近50期' },
  { value: 100, label: '近100期' },
  { value: 200, label: '近200期' },
]
const size = ref('all')

// 期数多时（全部约 2400 期）先显示一部分，往下滑再自动加载，统计行仍按全部期数计算
const PAGE = 150
const shown = ref(PAGE)
const sentinel = ref()
let observer
onMounted(() => {
  observer = new IntersectionObserver(
    ([e]) => e.isIntersecting && shown.value < grid.value.rows.length && (shown.value += PAGE),
    { rootMargin: '600px' },
  )
  observer.observe(sentinel.value)
})
onBeforeUnmount(() => observer?.disconnect())

// 点一行展开这一期的 7 个号码
const openIdx = ref(null)
const toggle = (idx) => (openIdx.value = openIdx.value === idx ? null : idx)

// 走势网格：开出的格子显示生肖；没开出的格子显示已连续几期未出
const grid = computed(() => {
  const N = props.draws.length
  const from = size.value === 'all' ? props.start : Math.max(props.start, N - size.value)
  const miss = Object.fromEntries(ZODIACS.map((z) => [z, 0]))
  const rows = []
  props.draws.forEach((d, i) => {
    const hit = SCOPES[props.scope](d)
    const cells = ZODIACS.map((z) => {
      if (hit.includes(z)) {
        miss[z] = 0
        return { hit: true, special: d.zodiacs[6] === z }
      }
      return { hit: false, miss: ++miss[z] }
    })
    if (i >= from) rows.push({ d, cells })
  })
  // 最长未出 = 表格里灰色数字的最大值（未出从范围之前开始的也算全），与生肖总表口径一致
  const summary = ZODIACS.map((z, j) => ({
    maxRun: Math.max(0, ...rows.map((r) => (r.cells[j].hit ? 0 : r.cells[j].miss))),
  }))
  // 标出每个生肖达到最长未出的那一格
  rows.forEach((r) => r.cells.forEach((c, j) => (c.peak = !c.hit && c.miss === summary[j].maxRun)))
  const top = Math.max(...summary.map((x) => x.maxRun))
  return { rows: rows.reverse(), summary, top }
})
watch(grid, () => (shown.value = PAGE))
const visibleRows = computed(() => grid.value.rows.slice(0, shown.value))

// 范围说明：跨年时带上日期，否则期号分不清是哪一年
const rangeText = computed(() => {
  const first = grid.value.rows.at(-1).d
  const last = grid.value.rows[0].d
  return first.year === last.year
    ? `第${first.issue}期 ~ 第${last.issue}期`
    : `${first.date} 第${first.issue}期 ~ ${last.date} 第${last.issue}期`
})
</script>

<template>
  <section class="card tight">
    <div class="card-head pad">
      <h2 class="card-title">生肖走势图</h2>
      <span class="card-meta">{{ range }}</span>
    </div>
    <div class="pad"><Seg v-model="size" :options="SIZES" block /></div>
    <p class="range-note pad"><b>{{ rangeText }}</b> · 共 {{ grid.rows.length }} 期 · 点一行看号码</p>
    <p class="card-help pad">灰色数字：连续几期没开出 · <span class="peak-text">橙色</span>：最长未出<template v-if="SHOW_SPECIAL && scope === '平码'"> · 橙圈：特码</template></p>
    <div class="scroll-x">
      <table class="trend">
        <thead>
          <tr>
            <th class="issue">期号</th>
            <th v-for="z in ZODIACS" :key="z" :class="{ bm: z === bm }">{{ z }}</th>
          </tr>
        </thead>
        <tbody>
          <tr class="sum key last">
            <td class="issue">最长<br />未出</td>
            <td v-for="(s, j) in grid.summary" :key="j">
              <span :class="{ top: s.maxRun === grid.top }">{{ s.maxRun }}</span>
            </td>
          </tr>
          <template v-for="r in visibleRows" :key="r.d.idx">
            <tr class="draw-row" :class="{ open: openIdx === r.d.idx }" @click="toggle(r.d.idx)">
              <td class="issue">
                <div class="num">{{ r.d.issue }}</div>
                <div class="muted date">{{ shortDate(r.d.date) }}</div>
              </td>
              <td v-for="(c, j) in r.cells" :key="j">
                <span v-if="c.hit" class="hit" :class="{ special: SHOW_SPECIAL && scope === '平码' && c.special }">{{ ZODIACS[j] }}</span>
                <span v-else class="miss" :class="{ peak: c.peak }">{{ c.miss }}</span>
              </td>
            </tr>
            <tr v-if="openIdx === r.d.idx" class="detail">
              <td :colspan="ZODIACS.length + 1">
                <div class="detail-inner">
                  <span class="muted small">第{{ r.d.issue }}期 {{ r.d.date }}</span>
                  <DrawBalls :draw="r.d" size="sm" />
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
    <div ref="sentinel" class="more muted small">
      <template v-if="shown < grid.rows.length">已显示 {{ shown }} / {{ grid.rows.length }} 期，往下滑继续加载…</template>
    </div>
  </section>
</template>

<style scoped>
.trend { border-collapse: collapse; width: 100%; font-size: 12px; font-variant-numeric: tabular-nums; }
.trend th, .trend td { text-align: center; padding: 3px 0; border-bottom: 1px solid var(--line); min-width: 23px; }
.trend th { color: var(--muted); font-weight: 500; font-size: 13px; position: sticky; top: 0; background: var(--surface); }
.trend th.bm { color: var(--accent); }
.trend th:nth-child(2), .trend .draw-row td:nth-child(2), .trend .sum td:nth-child(2) { padding-left: 5px; }
.trend .issue { text-align: left; position: sticky; left: 0; background: var(--surface); z-index: 1; padding-right: 4px; min-width: 36px; }
.trend .date { font-size: 10px; }
.trend .sum td { color: var(--ink-2); font-weight: 600; background: var(--surface-2); font-size: 10.5px; letter-spacing: -0.3px; padding: 4px 1px; }
.trend .sum .issue { font-size: 10px; font-weight: 500; line-height: 1.3; color: var(--muted); }
.trend .sum.last td { border-bottom: 2px solid var(--line); }
.trend .sum.key td { background: var(--accent-soft); color: var(--accent); font-size: 14px; font-weight: 700; letter-spacing: 0; padding: 6px 1px; }
.trend .sum.key .issue { color: var(--accent); font-weight: 700; font-size: 11px; }
.trend .sum.key .top {
  display: inline-flex; align-items: center; justify-content: center; min-width: 22px; height: 22px;
  padding: 0 3px; border-radius: 11px; background: var(--accent); color: #fff;
}
.miss.peak { color: var(--accent); font-weight: 700; opacity: 1; font-size: 12px; }
.peak-text { color: var(--accent); font-weight: 600; }
.more { text-align: center; padding-top: 10px; min-height: 1px; }
.range-note { margin: 12px 0 4px; font-size: 13px; color: var(--ink-2); }
/* 表格贴边以放下 12 列，文字区保持和其他卡片一样的内边距 */
@media (max-width: 480px) { .pad { padding: 0 4px; } }
.hit {
  display: inline-flex; align-items: center; justify-content: center; width: 20px; height: 20px;
  border-radius: 50%; background: var(--series); color: #fff; font-weight: 600; font-size: 11px;
}
.hit.special { box-shadow: 0 0 0 2px var(--surface), 0 0 0 4px var(--accent); }
.miss { color: var(--muted); opacity: 0.7; font-size: 11px; }
.draw-row { cursor: pointer; }
.draw-row:hover td, .draw-row.open td { background: var(--surface-2); }
.detail td { background: var(--surface-2); text-align: left; padding: 8px 6px 10px; }
.detail-inner { display: flex; flex-direction: column; gap: 6px; position: sticky; left: 6px; width: max-content; }
</style>
