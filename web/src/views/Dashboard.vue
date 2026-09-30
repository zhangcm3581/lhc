<script setup>
import { computed } from 'vue'
import { zodiacStats } from '../lib/stats.js'
import { PROB, SCOPES } from '../lib/zodiac.js'
import { pct, fix } from '../lib/format.js'
import Ball from '../components/Ball.vue'
import DrawBalls from '../components/DrawBalls.vue'

const props = defineProps({ draws: Array, scope: String, range: String, start: Number })

const latest = computed(() => props.draws.at(-1))
const bm = computed(() => latest.value.bm)
const rows = computed(() => zodiacStats(props.draws, props.scope, props.start))
const bmRow = computed(() => rows.value.find((r) => r.isBenming))

// 特码看最久未出前 5；平码每期出好几个生肖，未出都很短，列出全部 12 个，本命放最前
const ranked = computed(() =>
  [...rows.value].sort((a, b) => b.cur - a.cur || (b.times ?? 0) - (a.times ?? 0)),
)
const list = computed(() =>
  props.scope === '特码'
    ? ranked.value.slice(0, 5)
    : [...ranked.value.filter((r) => r.isBenming), ...ranked.value.filter((r) => !r.isBenming)],
)

// 本命按每期当时的本命计算（春节前后本命不同）
const hitsBm = (d) => SCOPES[props.scope](d).includes(d.bm)
const bmPeriod = computed(() => {
  let i = props.draws.length - 1
  while (i > 0 && props.draws[i - 1].bm === bm.value) i--
  const list = props.draws.slice(i)
  return { from: list[0].date, n: list.length, hits: list.filter(hitsBm).length }
})
const barWidth = (v, max) => `${Math.min(100, (v / max) * 100)}%`
</script>

<template>
  <section class="card">
    <div class="card-head">
      <h2 class="card-title">第 <span class="issue digits">{{ latest.issue }}</span> 期开奖</h2>
      <span class="card-meta">{{ latest.date }}</span>
    </div>
    <DrawBalls :draw="latest" :highlight="bm" size="lg" spread />
  </section>

  <section class="card">
    <div class="card-head">
      <h2 class="card-title">本命生肖「{{ bm }}」</h2>
      <span class="card-meta">{{ latest.year }} {{ bm }}年 · {{ bmPeriod.from.slice(5) }} 春节起</span>
    </div>
    <div class="bm-line">
      <span class="bm-avatar">{{ bm }}</span>
      <div class="bm-balls"><Ball v-for="n in bmRow.numbers" :key="n" :n="n" /></div>
    </div>
    <div class="grid-tiles two">
      <div class="tile">
        <div class="tile-label">{{ scope }}当前未出</div>
        <div v-if="bmRow.cur === 0" class="tile-value fresh">最新一期开出</div>
        <div v-else class="tile-value">{{ bmRow.cur }}<span class="unit">期</span></div>
        <div class="tile-sub">平均间隔 {{ fix(bmRow.avgGap) }} 期</div>
      </div>
      <div class="tile">
        <div class="tile-label">{{ bm }}年以来{{ scope }}出现</div>
        <div class="tile-value">{{ pct(bmPeriod.hits / bmPeriod.n) }}</div>
        <div class="tile-sub">{{ bmPeriod.hits }}/{{ bmPeriod.n }} 期 · 理论 {{ pct(PROB[scope](5)) }}</div>
      </div>
    </div>
  </section>

  <section class="card">
    <div class="card-head">
      <h2 class="card-title">{{ scope === '特码' ? '特码最久未出 Top5' : '12 生肖未出排行' }}</h2>
      <span class="card-meta">{{ range }}</span>
    </div>
    <p class="card-help">条：当前未出（满格 = 最长未出）· 竖线：平均间隔</p>
    <ul class="rank">
      <li v-for="r in list" :key="r.z" :class="{ bm: r.isBenming }">
        <span class="avatar">{{ r.z }}</span>
        <div class="body">
          <div class="head">
            <span v-if="r.cur === 0" class="cur fresh">最新一期开出</span>
            <span v-else class="cur">已连续 <b class="digits">{{ r.cur }}</b> 期未出</span>
            <span v-if="r.isBenming" class="bm-tag">本命</span>
            <span class="spacer"></span>
            <span v-if="r.atMax && r.cur > 0" class="tag tag-hot">{{ range === '全部' ? '历史' : '今年' }}最长</span>
            <span v-else-if="r.times >= 2" class="tag tag-accent">平时的 {{ fix(r.times) }} 倍</span>
          </div>
          <div class="bar" :title="`最长未出 ${r.maxGap} 期`">
            <div class="fill" :class="{ warm: r.times >= 2 }" :style="{ width: barWidth(r.cur, r.maxGap) }"></div>
            <div class="avg" :style="{ left: barWidth(r.avgGap ?? 0, r.maxGap) }"></div>
          </div>
          <div class="meta num">平均间隔 {{ fix(r.avgGap) }} · 最长未出 {{ r.maxGap }}</div>
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.issue { font-size: 20px; color: var(--accent); margin: 0 1px; }
.bm-line { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.bm-avatar {
  flex: none; width: 44px; height: 44px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;
  background: var(--accent); color: #fff; font-size: 22px; font-weight: 700;
}
.bm-balls { display: flex; gap: 6px; flex-wrap: wrap; }
.grid-tiles.two { grid-template-columns: 1fr 1fr; }
.rank { list-style: none; margin: 0; padding: 0; }
.rank li { display: flex; align-items: center; gap: 12px; padding: 12px 4px; border-bottom: 1px solid var(--line); }
.rank li:last-child { border-bottom: 0; }
/* 本命：浅橙底色的卡片，与其他生肖区分 */
.rank li.bm {
  background: var(--accent-soft); border: 1px solid var(--accent); border-radius: 12px;
  padding: 12px 10px; margin-bottom: 6px;
}
.avatar {
  flex: none; width: 36px; height: 36px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 17px; font-weight: 700; background: var(--bg); color: var(--ink);
}
.bm .avatar { background: var(--accent); color: #fff; border-color: var(--accent); }
.body { flex: 1; min-width: 0; }
.head { display: flex; align-items: center; gap: 6px; min-height: 24px; }
.cur { font-size: 15px; color: var(--ink); white-space: nowrap; }
.cur b { font-size: 20px; margin: 0 2px; }
.cur.fresh { color: var(--good); font-weight: 600; }
.bm-tag { font-size: 11px; line-height: 16px; padding: 0 5px; border-radius: 4px; color: #fff; background: var(--accent); }
.spacer { flex: 1; }
.bar { position: relative; height: 6px; background: var(--line); border-radius: 3px; margin: 7px 0 5px; overflow: hidden; }
.bm .bar { background: rgba(232, 89, 12, 0.18); }
.fill { position: absolute; inset: 0 auto 0 0; background: var(--series); border-radius: 3px; }
.fill.warm { background: var(--accent); }
.avg { position: absolute; top: -1px; bottom: -1px; width: 2px; background: var(--ink); opacity: 0.5; }
.meta { font-size: 12px; color: var(--muted); }
</style>
