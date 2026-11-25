<script setup>
import { computed, ref } from 'vue'
import { beijingToday } from '../lib/ledger.js'

const props = defineProps({ modelValue: String, mode: { type: String, default: 'date' }, label: String })
const emit = defineEmits(['update:modelValue'])
const dialog = ref()
const year = ref(2026)
const month = ref(1)
const view = ref('date')
const yearPage = ref(2020)
const weekdays = ['一', '二', '三', '四', '五', '六', '日']
const label = computed(() => props.modelValue ? props.mode === 'month' ? `${props.modelValue.slice(0, 4)} 年 ${Number(props.modelValue.slice(5, 7))} 月` : props.modelValue.replaceAll('-', ' / ') : '请选择日期')
const monthString = computed(() => `${year.value}-${String(month.value).padStart(2, '0')}`)
const days = computed(() => {
  const offset = (new Date(Date.UTC(year.value, month.value - 1, 1)).getUTCDay() + 6) % 7
  const count = new Date(Date.UTC(year.value, month.value, 0)).getUTCDate()
  return Array.from({ length: Math.ceil((offset + count) / 7) * 7 }, (_, i) => i >= offset && i < offset + count ? i - offset + 1 : null)
})
const years = computed(() => Array.from({ length: 12 }, (_, i) => yearPage.value + i).filter(y => y <= 2100))
function open() {
  const value = props.modelValue || beijingToday()
  year.value = Number(value.slice(0, 4)); month.value = Number(value.slice(5, 7))
  yearPage.value = 2020 + Math.floor((year.value - 2020) / 12) * 12
  view.value = props.mode
  dialog.value.showModal()
}
function caption() {
  yearPage.value = 2020 + Math.floor((year.value - 2020) / 12) * 12
  view.value = view.value === 'year' ? 'month' : 'year'
}
function choose(value) { emit('update:modelValue', value); dialog.value.close() }
function chooseMonth(m) {
  month.value = m
  if (props.mode === 'month') choose(monthString.value)
  else view.value = 'date'
}
function move(delta) {
  if (view.value === 'year') yearPage.value = Math.min(2092, Math.max(2020, yearPage.value + delta * 12))
  else if (view.value === 'month') year.value = Math.min(2100, Math.max(2020, year.value + delta))
  else {
    const next = new Date(Date.UTC(year.value, month.value - 1 + delta, 1))
    if (next.getUTCFullYear() < 2020 || next.getUTCFullYear() > 2100) return
    year.value = next.getUTCFullYear(); month.value = next.getUTCMonth() + 1
  }
}
function today() { choose(beijingToday().slice(0, props.mode === 'month' ? 7 : 10)) }
</script>

<template>
  <button type="button" class="date-trigger" :aria-label="label ? `${props.label || '日期'}：${label}` : props.label" aria-haspopup="dialog" @click="open"><span>{{ label }}</span><span aria-hidden="true">▦</span></button>
  <dialog ref="dialog" class="calendar" :aria-label="props.label || (mode === 'month' ? '选择年月' : '选择日期')" @click="$event.target === dialog && dialog.close()">
    <div class="calendar-head"><strong>{{ props.label || (mode === 'month' ? '选择年月' : '选择日期') }}</strong><button type="button" class="close" aria-label="关闭日期选择" @click="dialog.close()">×</button></div>
    <div class="calendar-nav">
      <button type="button" aria-label="上一个时间范围" @click="move(-1)">‹</button>
      <button type="button" class="calendar-caption" @click="caption">{{ view === 'year' ? `${yearPage} — ${Math.min(yearPage + 11, 2100)}` : `${year} 年${view === 'date' ? ` ${month} 月` : ''}` }} <span aria-hidden="true">⌄</span></button>
      <button type="button" aria-label="下一个时间范围" @click="move(1)">›</button>
    </div>
    <div v-if="view === 'year'" class="month-grid"><button v-for="y in years" :key="y" type="button" :class="{ active: y === year }" @click="year = y; view = 'month'">{{ y }} 年</button></div>
    <div v-else-if="view === 'month'" class="month-grid"><button v-for="m in 12" :key="m" type="button" :class="{ active: m === month }" @click="chooseMonth(m)">{{ m }} 月</button></div>
    <template v-else>
      <div class="weekdays"><span v-for="w in weekdays" :key="w">{{ w }}</span></div>
      <div class="day-grid"><template v-for="(day, i) in days" :key="i"><button v-if="day" type="button" :aria-label="`${monthString}-${String(day).padStart(2, '0')}`" :aria-pressed="modelValue === `${monthString}-${String(day).padStart(2, '0')}`" :class="{ active: modelValue === `${monthString}-${String(day).padStart(2, '0')}`, today: beijingToday() === `${monthString}-${String(day).padStart(2, '0')}` }" @click="choose(`${monthString}-${String(day).padStart(2, '0')}`)">{{ day }}</button><span v-else /></template></div>
    </template>
    <div class="calendar-footer"><button type="button" @click="today">{{ mode === 'month' ? '本月' : '今天' }}</button><button type="button" @click="dialog.close()">取消</button></div>
  </dialog>
</template>

<style scoped>
.date-trigger { width: 100%; display: flex; align-items: center; justify-content: space-between; gap: 10px; min-height: 44px; background: var(--surface-2); border: 1px solid var(--line); border-radius: 9px; padding: 10px 12px; cursor: pointer; text-align: left; }
.date-trigger > span:last-child { color: var(--muted); }
.calendar { width: min(360px, calc(100vw - 24px)); max-height: calc(100dvh - 32px); overflow-y: auto; padding: 18px; border: 1px solid var(--line); border-radius: 16px; background: var(--surface); color: var(--ink); box-shadow: 0 20px 70px #0003; }
.calendar::backdrop { background: #0005; }
.calendar-head, .calendar-nav, .calendar-footer { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.calendar button { cursor: pointer; border: 0; border-radius: 8px; background: var(--surface-2); min-height: 40px; }
.calendar .close { width: 32px; min-height: 32px; font-size: 24px; border-radius: 50%; }
.calendar-nav { margin: 16px 0; }
.calendar-nav > button { padding: 6px 12px; }
.calendar-caption { flex: 1; font-weight: 600; }
.weekdays, .day-grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 4px; text-align: center; }
.weekdays { color: var(--muted); font-size: 12px; margin-bottom: 8px; }
.day-grid button { background: transparent; }
.month-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
.month-grid button { min-height: 48px; }
.calendar button.active { background: var(--accent); color: white; font-weight: 600; }
.day-grid .today:not(.active) { color: var(--accent); box-shadow: inset 0 0 0 1px var(--accent); }
.calendar-footer { margin-top: 16px; border-top: 1px solid var(--line); padding-top: 12px; }
.calendar-footer button { background: transparent; color: var(--series); padding: 6px 12px; }
</style>
