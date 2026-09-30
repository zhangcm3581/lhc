<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { prepare, rangeStart } from './lib/stats.js'
import { remember, persist } from './lib/format.js'
import { SHOW_SPECIAL } from './lib/config.js'
import Seg from './components/Seg.vue'
import Dashboard from './views/Dashboard.vue'
import Missing from './views/Missing.vue'
import Trend from './views/Trend.vue'
import Benming from './views/Benming.vue'
import Relation from './views/Relation.vue'
import Structure from './views/Structure.vue'
import Backtest from './views/Backtest.vue'

const TABS = [
  { key: 'dash', label: '看板', comp: Dashboard },
  { key: 'miss', label: '未出分析', comp: Missing },
  { key: 'trend', label: '走势图', comp: Trend },
  { key: 'bm', label: '本命生肖', comp: Benming },
  { key: 'rel', label: '连出关联', comp: Relation },
  { key: 'struct', label: '单期结构', comp: Structure },
  { key: 'bt', label: '规则回测', comp: Backtest },
]

const draws = ref(null)
const error = ref('')
const scope = ref(SHOW_SPECIAL ? remember('scope', '平码') : '平码')
// 每次打开默认看今年
const range = ref('今年')
// 标签页跟随网址 #，方便收藏或分享某一页
const validTab = (k) => TABS.some((t) => t.key === k)
const hashTab = () => location.hash.slice(1)
const tab = ref(validTab(hashTab()) ? hashTab() : validTab(remember('tab')) ? remember('tab') : 'dash')
watch(scope, (v) => persist('scope', v))
watch(tab, (v) => {
  persist('tab', v)
  history.replaceState(null, '', '#' + v)
}, { immediate: true })
addEventListener('hashchange', () => validTab(hashTab()) && (tab.value = hashTab()))

// 手机上标签栏放不下时，把选中的标签滚到中间
const tabsEl = ref()
const revealTab = () =>
  nextTick(() => tabsEl.value?.querySelector('.on')?.scrollIntoView({ block: 'nearest', inline: 'center', behavior: 'smooth' }))
watch(tab, revealTab)
onMounted(revealTab)

const latest = computed(() => draws.value?.at(-1))
const start = computed(() => (draws.value ? rangeStart(draws.value, range.value) : 0))
const current = computed(() => TABS.find((t) => t.key === tab.value))

onMounted(async () => {
  try {
    const res = await fetch('data/draws.json', { cache: 'no-cache' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    draws.value = prepare(await res.json())
  } catch (e) {
    error.value = `数据加载失败：${e.message}`
  }
})
</script>

<template>
  <header class="app-head">
    <div class="container">
      <h1>生肖<span class="scope">【{{ scope }}】</span>走势分析</h1>
      <div v-if="latest" class="meta">最新 第{{ latest.issue }}期 · {{ latest.date }} · 共 {{ draws.length }} 期</div>
      <div class="filters">
        <Seg v-if="SHOW_SPECIAL" v-model="scope" :options="[{ value: '特码', label: '特码' }, { value: '平码', label: '平码' }]" block />
        <Seg
          v-model="range"
          block
          :options="[
            { value: '今年', label: '今年', sub: latest && `${latest.year}` },
            { value: '全部', label: '全部', sub: draws && `${draws[0].year}起` },
          ]"
        />
      </div>
    </div>
  </header>

  <nav class="tabs-bar">
    <div class="container">
      <div ref="tabsEl" class="tabs">
        <button v-for="t in TABS" :key="t.key" :class="{ on: tab === t.key }" @click="tab = t.key">{{ t.label }}</button>
      </div>
    </div>
  </nav>

  <main class="container main">
    <p v-if="error" class="card">{{ error }}</p>
    <p v-else-if="!draws" class="card muted">加载中…</p>
    <component :is="current.comp" v-else :draws="draws" :scope="scope" :range="range" :start="start" />
  </main>
</template>

<style scoped>
/* 顶部：标题、最新期数、时间范围上下排列，留足空间 */
.app-head { background: var(--surface); padding: 22px 0 16px; }
h1 { font-size: 22px; font-weight: 700; letter-spacing: 0.5px; line-height: 1.35; }
.scope { color: var(--accent); }
.meta { color: var(--muted); font-size: 13px; margin-top: 6px; font-variant-numeric: tabular-nums; }
.filters { display: flex; gap: 8px; margin-top: 16px; max-width: 400px; }

/* 标签栏固定在顶部 */
.tabs-bar { position: sticky; top: 0; z-index: 10; background: var(--surface); border-top: 1px solid var(--line); box-shadow: 0 1px 0 var(--line); }
.tabs { display: flex; overflow-x: auto; margin: 0 -16px; padding: 0 8px; scrollbar-width: none; }
.tabs::-webkit-scrollbar { display: none; }
.tabs button {
  position: relative; flex: none; border: 0; background: none; cursor: pointer; white-space: nowrap;
  padding: 12px 10px 13px; font-size: 15px; color: var(--ink-2);
}
.tabs button.on { color: var(--ink); font-weight: 600; }
.tabs button.on::after {
  content: ''; position: absolute; left: 50%; bottom: 5px; transform: translateX(-50%);
  width: 18px; height: 3px; border-radius: 2px; background: var(--accent);
}
.main { padding-top: 12px; padding-bottom: 40px; }
@media (max-width: 480px) {
  .tabs { margin: 0 -8px; padding: 0 2px; }
}
</style>
