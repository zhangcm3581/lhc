<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { pad } from '../lib/zodiac.js'

const records = ref([])
const loading = ref(true)
const error = ref('')
const year = ref(0)
const issue = ref(0)
const expanded = ref(false)
const picker = ref()
function openPicker() {
  picker.value.showModal()
  const current = picker.value.querySelector('[aria-pressed="true"]')
  current?.focus({ preventScroll: true })
  current?.scrollIntoView({ block: 'nearest' })
}
function chooseIssue(value) {
  issue.value = value
  picker.value.close()
}
function moveOption(event) {
  const buttons = [...picker.value.querySelectorAll('.issue-option')]
  const index = buttons.indexOf(document.activeElement)
  const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1
    : event.key === 'ArrowDown' ? Math.min(index + 1, buttons.length - 1)
    : event.key === 'ArrowUp' ? Math.max(index - 1, 0) : null
  if (next !== null) { event.preventDefault(); buttons[next]?.focus() }
}
const years = computed(() => [...new Set(records.value.map(r => r.year))].sort((a, b) => b - a))
const issues = computed(() => records.value.filter(r => r.year === year.value).sort((a, b) => b.issue - a.issue))
const selectedIndex = computed(() => issues.value.findIndex(r => r.issue === issue.value))
const visibleIssues = computed(() => {
  if (expanded.value) return issues.value
  const start = Math.max(0, Math.min(selectedIndex.value - 3, issues.value.length - 8))
  return issues.value.slice(start, start + 8)
})
const selected = computed(() => issues.value.find(r => r.issue === issue.value))
const result = computed(() => selected.value?.rows[0].result)
const stamp = value => value?.replace('T', ' ').replace(/\+08:00$/, '')
watch(year, () => { issue.value = issues.value[0]?.issue ?? 0 })

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch('data/materials.json', { cache: 'no-cache' })
    if (!res.ok) throw new Error(res.status === 404 ? '尚未采集资料，请先运行资料采集脚本。' : `HTTP ${res.status}`)
    const data = await res.json()
    if (!Array.isArray(data)) throw new Error('资料文件格式不正确')
    records.value = data
    year.value = years.value[0] ?? 0
    issue.value = issues.value[0]?.issue ?? 0
  } catch (e) {
    error.value = `资料加载失败：${e.message}`
  } finally {
    loading.value = false
  }
}
onMounted(load)
const hit = row => row.result && (row.zodiacs.length ? row.zodiacs.includes(row.result.zodiac) : row.numbers.includes(row.result.number))
</script>

<template>
  <section v-if="loading" class="card muted" role="status">正在加载资料…</section>
  <section v-else-if="error" class="card" role="alert">
    <p>{{ error }}</p><button class="chip" @click="load">重新加载</button>
  </section>
  <section v-else-if="!records.length" class="card muted">暂无已保存资料。</section>
  <template v-else>
    <section class="card">
      <div class="card-head">
        <h2 class="card-title">历史期数 <span class="count">共 {{ issues.length }} 期</span></h2>
        <label class="year">年份 <select v-model.number="year" aria-label="资料年份"><option v-for="y in years" :key="y" :value="y">{{ y }}</option></select></label>
      </div>
      <div class="issue-nav">
        <button class="chip" :disabled="selectedIndex >= issues.length - 1" @click="issue = issues[selectedIndex + 1].issue">‹ 上一期</button>
        <button class="issue-trigger" aria-haspopup="dialog" @click="openPicker">
          <strong>第 {{ issue }} 期</strong><span>{{ selected?.date.slice(5) }}</span><span aria-hidden="true">⌄</span>
        </button>
        <button class="chip" :disabled="selectedIndex <= 0" @click="issue = issues[selectedIndex - 1].issue">下一期 ›</button>
      </div>
      <dialog ref="picker" class="issue-picker" aria-labelledby="issue-picker-title" @click="($event.target === picker) && picker.close()">
        <div class="picker-head">
          <div><h2 id="issue-picker-title">选择期号</h2><p>{{ year }} 年 · 共 {{ issues.length }} 期</p></div>
          <button class="picker-close" aria-label="关闭期号选择" @click="picker.close()">×</button>
        </div>
        <div class="picker-options" @keydown="moveOption">
          <button v-for="r in issues" :key="r.issue" class="issue-option" :aria-pressed="issue === r.issue" @click="chooseIssue(r.issue)">
            <strong>第 {{ r.issue }} 期</strong><span class="option-date">{{ r.date.slice(5).replace('-', ' / ') }}</span>
            <span class="option-status">{{ r.rows[0].result ? '已开奖' : '待开奖' }}</span>
            <span class="option-check" aria-hidden="true">{{ issue === r.issue ? '✓' : '' }}</span>
          </button>
        </div>
      </dialog>
      <div class="issues" aria-label="快速选择期号">
        <button v-for="r in visibleIssues" :key="r.issue" class="chip" :class="{ on: issue === r.issue }" :aria-pressed="issue === r.issue" @click="issue = r.issue">{{ r.issue }}期</button>
      </div>
      <div class="issue-actions">
        <button v-if="issues.length > 8" class="text-button" :aria-expanded="expanded" @click="expanded = !expanded">{{ expanded ? '收起期数 ↑' : '展开全部期数 ↓' }}</button>
        <button v-if="selectedIndex > 0" class="text-button" @click="issue = issues[0].issue">回到最新一期</button>
      </div>
    </section>

    <section v-if="selected" class="card">
      <div class="card-head detail-head">
        <div>
          <h2 class="card-title">{{ selected.year }} 年 · 第 {{ selected.issue }} 期</h2>
          <p class="date muted small">{{ selected.date }}（按期号推算）</p>
        </div>
        <div class="result"><span class="muted small">原站开奖</span><strong>{{ result ? `${result.zodiac} ${pad(result.number)}` : '待开奖' }}</strong></div>
      </div>
      <table class="materials-table">
        <thead><tr><th scope="col">栏目</th><th scope="col">原站资料</th><th scope="col">对照结果</th></tr></thead>
        <tbody>
          <tr v-for="row in selected.rows" :key="row.label">
            <th scope="row">{{ row.label }}</th>
            <td>
              <div class="tokens">
                <span v-for="z in row.zodiacs" :key="z" class="token" :class="{ matched: row.result?.zodiac === z }">{{ z }}</span>
                <span v-if="row.label === '一肖'" class="main-pick">主博 {{ pad(row.numbers[0]) }}</span>
                <template v-else><span v-for="n in row.numbers" :key="n" class="token digits" :class="{ matched: row.result?.number === n }">{{ pad(n) }}</span></template>
              </div>
            </td>
            <td><span v-if="!row.result" class="muted">待开奖</span><span v-else class="outcome" :class="{ won: hit(row) }">{{ hit(row) ? '命中' : '未中' }}</span></td>
          </tr>
        </tbody>
      </table>
      <div class="archive-note small muted">
        <details><summary>采集时间说明</summary><p>北京时间 10:00、12:00、13:00 补预测，21:29 补抓；21:34 起补结果，最晚到 22:40。采集成功即停止。</p></details>
        <p>预测保存于 {{ stamp(selected.captured_at) }}（北京时间）</p>
        <p v-if="selected.result_captured_at">结果同步于 {{ stamp(selected.result_captured_at) }}</p>
        <p v-if="selected.before_result">预测在原站未公布结果时保存；开奖后仅补结果，命中情况按已保存的预测计算。</p>
        <p v-else>历史补抓资料，首次采集时原站已公布结果，不代表开奖前的预测。</p>
        <a :href="selected.source" target="_blank" rel="noopener noreferrer">查看资料来源 ↗</a>
      </div>
    </section>
  </template>
</template>

<style scoped>
.year { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--ink-2); }
select { font: inherit; color: var(--ink); background: var(--surface-2); border: 1px solid var(--line); border-radius: 6px; padding: 6px 8px; max-width: 100%; }
.count { margin-left: 6px; font-size: 12px; font-weight: 400; color: var(--muted); }
.issue-nav { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 8px; margin: 16px 0 12px; }
.issue-trigger { display: flex; align-items: center; justify-content: center; gap: 8px; min-width: 0; border: 1px solid var(--line); border-radius: 8px; background: var(--surface-2); cursor: pointer; }
.issue-trigger span { font-size: 12px; color: var(--ink-2); }
.issue-picker { width: min(380px, calc(100vw - 32px)); max-height: calc(100dvh - 48px); padding: 0; border: 1px solid var(--line); border-radius: 16px; background: var(--surface); color: var(--ink); box-shadow: 0 20px 70px #0003; overflow: hidden; }
.issue-picker::backdrop { background: #0005; }
.picker-head { display: flex; align-items: center; justify-content: space-between; padding: 18px 20px 14px; border-bottom: 1px solid var(--line); }
.picker-head h2 { font-size: 17px; }
.picker-head p { margin: 4px 0 0; font-size: 12px; color: var(--muted); }
.picker-close { width: 32px; height: 32px; border: 0; border-radius: 50%; background: var(--surface-2); font-size: 24px; cursor: pointer; }
.picker-options { max-height: min(360px, calc(100dvh - 160px)); overflow-y: auto; overscroll-behavior: contain; padding: 8px; }
.issue-option { width: 100%; display: flex; align-items: center; gap: 12px; min-height: 48px; padding: 10px 12px; border: 0; border-radius: 8px; background: transparent; cursor: pointer; text-align: left; }
.issue-option:hover { background: var(--surface-2); }
.issue-option[aria-pressed="true"] { background: var(--accent-soft); color: var(--accent); }
.issue-option:focus-visible { outline-offset: -2px; }
.option-date { color: var(--ink-2); font-size: 13px; font-variant-numeric: tabular-nums; }
.option-status { margin-left: auto; color: var(--muted); font-size: 12px; }
.option-check { width: 16px; color: var(--accent); font-weight: 700; }
.issue-nav button { padding: 10px 8px; white-space: nowrap; }
.issue-nav button:disabled { opacity: .35; cursor: default; }
.issues { display: grid; grid-template-columns: repeat(8, minmax(0, 1fr)); gap: 8px; }
.issues button { padding: 8px 0; }
.issue-actions { display: flex; justify-content: space-between; gap: 12px; margin-top: 10px; }
.text-button { border: 0; background: none; padding: 4px 0; color: var(--series); cursor: pointer; font-size: 12px; }
summary { cursor: pointer; }
@media (max-width: 600px) { .issues { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
.detail-head { align-items: center; }
.date { margin: 5px 0 0; }
.result { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; }
.result strong { font-size: 22px; color: var(--accent); }
.materials-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.materials-table th, .materials-table td { text-align: left; border-bottom: 1px solid var(--line); padding: 14px 8px; }
.materials-table thead th { font-size: 12px; color: var(--muted); font-weight: 400; }
.materials-table tbody th { width: 100px; white-space: nowrap; font-weight: 500; }
.materials-table td:last-child, .materials-table th:last-child { width: 72px; text-align: right; white-space: nowrap; }
.tokens { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.token { display: inline-flex; align-items: center; justify-content: center; min-width: 30px; height: 30px; border-radius: 6px; background: var(--surface-2); font-weight: 600; }
.token.matched { background: var(--accent-soft); color: var(--accent); box-shadow: inset 0 0 0 1px var(--accent); }
.main-pick { color: var(--series); font-weight: 600; margin-left: 4px; }
.outcome { color: var(--muted); }
.outcome.won { color: var(--good); font-weight: 600; }
.archive-note { margin-top: 16px; line-height: 1.7; }
.archive-note p { margin: 4px 0; }
a { color: var(--series); }
@media (max-width: 480px) {
  .materials-table th, .materials-table td { padding: 12px 3px; }
  .materials-table tbody th { width: 76px; font-size: 12px; }
  .materials-table td:last-child, .materials-table th:last-child { width: 54px; font-size: 12px; }
  .tokens { gap: 4px; }
  .token { min-width: 27px; height: 28px; }
}
</style>
