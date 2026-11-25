<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import DatePicker from '../components/DatePicker.vue'
import { scoreToUnits, beijingToday, issueForDate, totals } from '../lib/ledger.js'

let authEpoch = 0
const unlocked = ref(false)
const checking = ref(true)
const pin = ref('')
const busy = ref(false)
const error = ref('')
const notice = ref('')
const records = ref([])
const month = ref(beijingToday().slice(0, 7))
const all = ref(false)
const refreshing = ref(false)
const synced = ref('')
const editor = ref()
const editing = ref(null)
const day = ref(beijingToday())
const issue = ref(issueForDate(day.value))
const direction = ref('win')
const amount = ref('')
const formError = ref('')
const saving = ref(false)
const filtered = computed(() => records.value.filter(r => all.value || r.date.startsWith(month.value)))
const summary = computed(() => totals(filtered.value))
const points = cents => (Math.abs(cents) / 100).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
const signed = cents => `${cents > 0 ? '+' : cents < 0 ? '−' : ''}${points(cents)} 分`
watch(day, value => { if (!editing.value) issue.value = issueForDate(value) })
watch(month, () => { all.value = false })

async function api(path, method = 'GET', body) {
  const res = await fetch(`/api/ledger/${path}`, { method, credentials: 'same-origin', cache: 'no-store', ...(body ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {}) })
  let data
  try { data = await res.json() } catch { throw new Error('记录服务暂未就绪，请稍后重试') }
  if (!res.ok) {
    if (res.status === 401 && path !== 'login') { unlocked.value = false; records.value = []; editor.value?.close() }
    throw Object.assign(new Error(data.error || '请求失败，请稍后重试'), { status: res.status })
  }
  return data
}
async function refresh(initial = false) {
  if (refreshing.value) return
  refreshing.value = true
  const epoch = authEpoch
  try {
    const data = await api('records')
    if (epoch !== authEpoch) return
    records.value = data.records
    unlocked.value = true
    error.value = ''
    synced.value = new Intl.DateTimeFormat('zh-CN', { timeZone: 'Asia/Shanghai', hour: '2-digit', minute: '2-digit' }).format(new Date())
  } catch (e) {
    if (!initial) error.value = e.message
    else if (e.status !== 401) error.value = e.message
  } finally { refreshing.value = false; checking.value = false }
}
async function login() {
  if (busy.value) return
  busy.value = true; error.value = ''
  try { await api('login', 'POST', { pin: pin.value }); pin.value = ''; await refresh() }
  catch (e) { error.value = e.message }
  finally { busy.value = false }
}
async function logout() {
  if (busy.value) return
  authEpoch++
  busy.value = true
  try { await api('logout', 'POST', {}); unlocked.value = false; records.value = []; notice.value = '' }
  catch (e) { error.value = e.message }
  finally { busy.value = false }
}
function openEditor(record = null) {
  editing.value = record
  day.value = record?.date || beijingToday()
  issue.value = record?.issue || issueForDate(day.value)
  direction.value = record && record.amount_cents < 0 ? 'loss' : 'win'
  amount.value = record ? (Math.abs(record.amount_cents) / 100).toFixed(2) : ''
  formError.value = ''; notice.value = ''
  editor.value.showModal()
}
function closeEditor() { if (!saving.value) editor.value.close() }
async function save() {
  if (saving.value) return
  formError.value = ''
  try {
    const issueNumber = Number(issue.value)
    const year = Number(day.value.slice(0, 4))
    if (!Number.isInteger(issueNumber) || issueNumber < 1 || issueNumber > issueForDate(`${year}-12-31`)) throw new Error('请输入有效期数')
    if (records.value.some(r => r.year === year && r.issue === issueNumber && r.id !== editing.value?.id)) throw new Error(`${year} 年第 ${issueNumber} 期已有记录，请编辑已有记录。`)
    const body = { date: day.value, issue: issueNumber, amount_cents: scoreToUnits(amount.value.trim(), direction.value), ...(editing.value ? { revision: editing.value.revision } : {}) }
    saving.value = true
    const result = await api(editing.value ? `records/${editing.value.id}` : 'records', editing.value ? 'PUT' : 'POST', body)
    records.value = [result.record, ...records.value.filter(r => r.id !== result.record.id)].sort((a, b) => b.date.localeCompare(a.date) || b.issue - a.issue)
    month.value = body.date.slice(0, 7); all.value = false
    editor.value.close()
    notice.value = '记录已保存，其他设备可同步查看'
    await refresh()
  } catch (e) { formError.value = e.message }
  finally { saving.value = false }
}
function syncVisible() { if (unlocked.value && !document.hidden && !saving.value && !busy.value) refresh() }
let timer
onMounted(() => {
  refresh(true)
  timer = setInterval(syncVisible, 30000)
  window.addEventListener('focus', syncVisible)
  document.addEventListener('visibilitychange', syncVisible)
})
onUnmounted(() => {
  clearInterval(timer)
  window.removeEventListener('focus', syncVisible)
  document.removeEventListener('visibilitychange', syncVisible)
})
</script>

<template>
  <p v-if="checking" class="card muted" role="status">正在连接共享记录…</p>
  <section v-else-if="!unlocked" class="card unlock">
    <div class="lock-symbol" aria-hidden="true"><svg width="30" height="34" viewBox="0 0 30 34" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="3" y="14" width="24" height="17" rx="4"/><path d="M8 14V9a7 7 0 0 1 14 0v5M15 21v4"/></svg></div>
    <h2>输入访问验证码</h2>
    <p class="muted">输入验证码，查看同一份共享记录</p>
    <form @submit.prevent="login">
      <label class="sr-only" for="ledger-pin">6 位数字验证码</label>
      <input id="ledger-pin" v-model="pin" class="pin" type="password" inputmode="numeric" autocomplete="current-password" pattern="[0-9]{6}" maxlength="6" placeholder="••••••" required :disabled="busy" aria-describedby="login-error" />
      <p v-if="error" id="login-error" class="error" role="alert">{{ error }}</p>
      <button class="primary" :disabled="busy || !/^[0-9]{6}$/.test(pin)">{{ busy ? '正在验证…' : '进入统计分' }}</button>
    </form>
  </section>
  <template v-else>
    <div class="ledger-toolbar"><span class="small muted">共享记录 · {{ refreshing ? '同步中…' : `${synced} 已同步` }}</span><div><button class="text-button" :disabled="refreshing" @click="refresh()">刷新</button><button class="text-button" :disabled="busy" @click="logout">退出</button></div></div>
    <p v-if="error" class="error card" role="alert">{{ error }}</p>
    <p v-if="notice" class="success small" role="status">{{ notice }}</p>
    <section class="card">
      <div class="filters"><div class="scope-toggle"><button :class="{ active: !all }" @click="all = false">按月</button><button :class="{ active: all }" @click="all = true">全部</button></div><DatePicker v-model="month" mode="month" label="统计年月" /></div>
      <div class="summary" :class="{ negative: summary.net < 0 }"><div class="small muted">{{ all ? '全部记录' : `${month.replace('-', ' 年 ')} 月` }} · 净得分</div><strong class="net digits">{{ signed(summary.net) }}</strong><div class="summary-parts"><div><span>累计加分</span><strong class="win digits">{{ points(summary.win) }} 分</strong></div><div><span>累计扣分</span><strong class="loss digits">{{ points(summary.loss) }} 分</strong></div></div></div>
    </section>
    <div class="list-title"><h2 class="card-title">分数明细 <span class="small muted">共 {{ filtered.length }} 条</span></h2><button class="primary add" @click="openEditor()">＋ 记一笔</button></div>
    <section class="card entries">
      <div v-if="!filtered.length" class="empty"><p>这个{{ all ? '记录列表' : '月份' }}还没有记录</p><span class="small muted">点击「记一笔」，输入日期、期数和加减分数</span></div>
      <div v-for="r in filtered" :key="r.id" class="entry"><div><strong>第 {{ r.issue }} 期</strong><div class="small muted">{{ r.date }}</div></div><strong class="entry-amount digits" :class="r.amount_cents > 0 ? 'win' : 'loss'">{{ signed(r.amount_cents) }}</strong><span class="outcome" :class="r.amount_cents > 0 ? 'win' : 'loss'">{{ r.amount_cents > 0 ? '加分' : '扣分' }}</span><button class="edit" :aria-label="`编辑 ${r.year} 年第 ${r.issue} 期`" @click="openEditor(r)">编辑</button></div>
    </section>
  </template>
  <dialog ref="editor" class="editor" aria-labelledby="ledger-editor-title" @cancel="saving && $event.preventDefault()" @click="$event.target === editor && closeEditor()">
    <div class="editor-head"><h2 id="ledger-editor-title">{{ editing ? '编辑记录' : '记录分数' }}</h2><button class="close" aria-label="关闭记录编辑" :disabled="saving" @click="closeEditor">×</button></div>
    <form @submit.prevent="save">
      <fieldset :disabled="saving">
        <div class="form-field"><span class="field-label">日期</span><DatePicker v-model="day" label="记录日期" /></div>
        <label class="form-field" for="ledger-issue"><span>期数</span><input id="ledger-issue" v-model="issue" inputmode="numeric" pattern="[0-9]{1,3}" required /><small class="muted">同一年同一期只能保存一条记录</small></label>
        <div class="direction" role="group" aria-label="加分或扣分"><button type="button" :class="{ chosen: direction === 'win', win: true }" :aria-pressed="direction === 'win'" @click="direction = 'win'">加分</button><button type="button" :class="{ chosen: direction === 'loss', loss: true }" :aria-pressed="direction === 'loss'" @click="direction = 'loss'">扣分</button></div>
        <label class="form-field" for="ledger-amount"><span>分数（分）</span><input id="ledger-amount" v-model="amount" class="amount digits" inputmode="decimal" placeholder="0.00" required /><small class="muted">选择加分或扣分后，输入分数即可</small></label>
        <p v-if="formError" class="error" role="alert">{{ formError }}</p>
        <button class="primary" :disabled="saving">{{ saving ? '正在保存…' : '保存记录' }}</button>
      </fieldset>
      <p class="small muted save-help">保存后，其他设备也能查看</p>
    </form>
  </dialog>
</template>

<style scoped>
button { cursor: pointer; } button:disabled { cursor: default; opacity: .5; }
.primary { background: var(--accent); color: white; border: 0; border-radius: 10px; min-height: 46px; padding: 10px 20px; font-weight: 600; width: 100%; }
.unlock { max-width: 420px; margin: 40px auto; padding: 32px 24px; text-align: center; }
.unlock h2 { font-size: 22px; }.unlock p { font-size: 13px; }
.lock-symbol { width: 56px; height: 56px; margin: 0 auto 20px; background: var(--accent-soft); border-radius: 16px; color: var(--accent); font-size: 42px; display: flex; align-items: center; justify-content: center; }
/* 手机浏览器聚焦小于 16px 的输入框时会自动放大页面。 */
input { width: 100%; min-width: 0; max-width: 100%; background: var(--surface-2); color: var(--ink); border: 1px solid var(--line); border-radius: 9px; padding: 12px; font: inherit; font-size: 16px; }
input:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.pin { text-align: center; font-size: 30px; letter-spacing: 12px; margin: 20px 0; padding-left: 24px; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
.ledger-toolbar, .list-title { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin: 0 0 12px; }
.text-button { background: none; border: 0; color: var(--series); font-size: 13px; padding: 8px; }
.filters { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 16px; align-items: center; margin-bottom: 16px; }
.scope-toggle { display: flex; padding: 3px; background: var(--surface-2); border-radius: 9px; }
.scope-toggle button { border: 0; background: none; padding: 7px 12px; border-radius: 7px; font-size: 13px; white-space: nowrap; }
.scope-toggle button.active { color: var(--accent); background: var(--accent-soft); font-weight: 600; }
.summary { padding: 20px 16px 16px; border-radius: 12px; background: var(--surface-2); text-align: center; }
.net { display: block; font-size: clamp(30px, 7vw, 40px); color: var(--good); margin: 6px 0 18px; overflow-wrap: anywhere; }
.negative .net { color: var(--hot); }
.summary-parts { display: grid; grid-template-columns: 1fr 1fr; border-top: 1px solid var(--line); padding-top: 14px; }
.summary-parts > div + div { border-left: 1px solid var(--line); }.summary-parts span { display: block; font-size: 12px; color: var(--ink-2); }.summary-parts strong { display: block; font-size: 21px; overflow-wrap: anywhere; }
.win, .success { color: var(--good); }.loss, .error { color: var(--hot); }.error { font-size: 13px; }
.add { width: auto; min-height: 40px; font-size: 14px; }.list-title { margin-top: 20px; }
.entries { padding-top: 0; padding-bottom: 0; }.entry { display: flex; align-items: center; gap: 10px; padding: 17px 0; border-bottom: 1px solid var(--line); }.entry:last-child { border-bottom: 0; }.entry > div { flex-shrink: 0; }.entry-amount { margin-left: auto; font-size: 20px; overflow-wrap: anywhere; min-width: 0; }.outcome { font-size: 12px; }.edit { border: 0; background: var(--surface-2); border-radius: 6px; padding: 8px; font-size: 12px; white-space: nowrap; }.empty { text-align: center; padding: 32px 8px; color: var(--ink-2); }
.editor { width: 420px; max-width: calc(100% - 24px); box-sizing: border-box; max-height: calc(100dvh - 32px); overflow-y: auto; overflow-x: hidden; padding: 24px; border: 1px solid var(--line); border-radius: 16px; background: var(--surface); color: var(--ink); box-shadow: 0 20px 70px #0003; }.editor::backdrop { background: #0005; }
.editor-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }.editor-head h2 { font-size: 20px; }.close { width: 32px; height: 32px; border: 0; border-radius: 50%; font-size: 24px; background: var(--surface-2); }
fieldset { border: 0; margin: 0; padding: 0; min-width: 0; }.form-field { min-width: 0; display: flex; flex-direction: column; gap: 8px; margin-bottom: 18px; }.form-field > span { font-weight: 600; }.form-field small { font-size: 12px; }.amount { font-size: 28px; font-weight: 600; }
.direction { display: flex; gap: 10px; margin: 8px 0 20px; }.direction button { flex: 1; border: 1px solid var(--line); background: var(--surface-2); border-radius: 10px; padding: 10px; font-weight: 600; font-size: 22px; }.direction button.chosen { border-color: currentColor; box-shadow: inset 0 0 0 1px currentColor; }.save-help { text-align: center; margin: 12px 0 0; }
@media (max-width: 400px) { .entry { gap: 6px; }.entry-amount { font-size: 17px; }.editor { padding: 18px; }.filters { gap: 8px; }.scope-toggle button { padding: 7px 9px; } }
</style>
