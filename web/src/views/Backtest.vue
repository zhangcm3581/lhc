<script setup>
import { ref, computed } from 'vue'
import { backtest, RULES } from '../lib/backtest.js'
import { pct, fix } from '../lib/format.js'
import Seg from '../components/Seg.vue'
import { SHOW_SPECIAL } from '../lib/config.js'

const props = defineProps({ draws: Array, scope: String, range: String, start: Number })
// 特码隐藏时不提供按特码选的规则
const ruleNames = Object.keys(RULES).filter((name) => SHOW_SPECIAL || name !== '上期特码生肖')
const rule = ref('最久未出')
const K = ref(3)
const win = ref(30)

const DESC = {
  最久未出: (k) => `每期选当前未出最久的 ${k} 个生肖`,
  近期最热: (k, w) => `每期选近 ${w} 期开出次数最多的 ${k} 个生肖`,
  近期最冷: (k, w) => `每期选近 ${w} 期开出次数最少的 ${k} 个生肖`,
  只选本命: () => '每期只选当时的本命生肖',
  上期特码生肖: () => '每期选上一期特码的生肖',
}

const r = computed(() => backtest(props.draws, props.scope, props.start, rule.value, K.value, win.value))
const verdict = computed(() => {
  const b = r.value.beat
  if (b >= 0.95) return { cls: 'tag-hot', text: '比随机选明显好' }
  if (b <= 0.05) return { cls: 'tag-cold', text: '比随机选明显差' }
  return { cls: 'tag-mid', text: '和随机选没有明显区别' }
})
</script>

<template>
  <section class="card">
    <div class="card-head">
      <h2 class="card-title">规则回测</h2>
      <span class="card-meta">{{ range }}</span>
    </div>
    <p class="card-help">按规则逐期模拟选生肖，和随机选对比</p>
    <div class="ctrl">
      <div class="label">规则</div>
      <div class="rule-grid">
        <button v-for="name in ruleNames" :key="name" class="chip" :class="{ on: rule === name }" @click="rule = name">{{ name }}</button>
      </div>
    </div>
    <div v-if="RULES[rule].usesK" class="ctrl">
      <div class="label">每期选几个</div>
      <Seg v-model="K" :options="[1, 2, 3, 4, 5, 6].map((v) => ({ value: v, label: `${v}个` }))" block />
    </div>
    <div v-if="RULES[rule].usesWindow" class="ctrl">
      <div class="label">统计近几期</div>
      <Seg v-model="win" :options="[10, 30, 50, 100].map((v) => ({ value: v, label: `${v}期` }))" block />
    </div>
    <p class="rule-desc">{{ DESC[rule](K, win) }}（{{ scope === '特码' ? '开出特码算中' : '7 个号里有就算中' }}）</p>
  </section>

  <section class="card">
    <div class="card-head">
      <h2 class="card-title">回测结果 <span class="tag verdict" :class="verdict.cls">{{ verdict.text }}</span></h2>
      <span class="card-meta">共 {{ r.rounds }} 期</span>
    </div>
    <div class="scroll-x">
      <table class="data">
        <thead>
          <tr><th></th><th>这条规则</th><th>随机选</th></tr>
        </thead>
        <tbody>
          <tr>
            <td>每个选中生肖的命中率</td>
            <td class="mine digits">{{ pct(r.hitRate, 2) }}</td>
            <td class="digits muted">{{ pct(r.random.hitRate, 2) }}</td>
          </tr>
          <tr>
            <td>每期至少中 1 个的比例</td>
            <td class="mine digits">{{ pct(r.anyRate, 2) }}</td>
            <td class="digits muted">{{ pct(r.random.anyRate, 2) }}</td>
          </tr>
          <tr>
            <td>最长连续全不中</td>
            <td class="mine"><span class="digits">{{ r.worstMiss }}</span> 期</td>
            <td class="muted"><span class="digits">{{ fix(r.random.worstMiss) }}</span> 期</td>
          </tr>
          <tr>
            <td>当前连续全不中</td>
            <td class="mine"><span class="digits">{{ r.currentMiss }}</span> 期</td>
            <td></td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="card-help foot">200 次随机选里，{{ pct(r.beat, 0) }} 不如这条规则（超过 95% 才算明显更好）</p>
  </section>

  <section class="card">
    <div class="card-head">
      <h2 class="card-title">按这条规则，下一期会选</h2>
    </div>
    <div class="next">
      <span v-for="z in r.next" :key="z" class="pick">{{ z }}</span>
    </div>
    <p class="card-help foot">只代表过去的表现</p>
  </section>
</template>

<style scoped>
.ctrl { margin-top: 12px; }
.label { color: var(--muted); font-size: 12px; margin-bottom: 6px; }
.rule-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(78px, 1fr)); gap: 8px; }
.rule-grid .chip { text-align: center; padding: 7px 0; }
.rule-desc { margin: 14px 0 0; padding: 10px 12px; border-radius: 10px; background: var(--surface-2); color: var(--ink-2); font-size: 14px; }
.verdict { margin-left: 6px; vertical-align: 2px; }
.mine { font-weight: 700; font-size: 15px; }
.foot { margin: 12px 0 0; }
.next { display: flex; gap: 10px; flex-wrap: wrap; }
.pick {
  width: 44px; height: 44px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;
  background: var(--accent-soft); color: var(--accent); font-size: 20px; font-weight: 700; border: 1px solid var(--accent);
}
</style>
