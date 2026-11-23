<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { pad } from '../lib/zodiac.js'

const records = ref([])
const loading = ref(true)
const error = ref('')
const year = ref(0)
const issue = ref(0)
const years = computed(() => [...new Set(records.value.map(r => r.year))].sort((a, b) => b - a))
const issues = computed(() => records.value.filter(r => r.year === year.value).sort((a, b) => b.issue - a.issue))
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
        <h2 class="card-title">六肖十码 · 历史资料</h2>
        <label class="year">年份 <select v-model.number="year" aria-label="资料年份"><option v-for="y in years" :key="y" :value="y">{{ y }}</option></select></label>
      </div>
      <p class="card-help">共保存 {{ records.length }} 期 · 10 / 12 / 13 点补预测 · 21:29 补抓 · 21:34 起补结果（北京时间），采到即停</p>
      <div class="issues" aria-label="选择期号">
        <button v-for="r in issues" :key="r.issue" class="chip" :class="{ on: issue === r.issue }" :aria-pressed="issue === r.issue" @click="issue = r.issue">{{ r.issue }}期</button>
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
.issues { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 8px; }
.issues button { flex: none; }
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
