<script setup>
// ECharts 封装：option 是一个函数，接收当前主题色，深色/浅色切换时自动重画
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, MarkLineComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([BarChart, LineChart, GridComponent, TooltipComponent, MarkLineComponent, CanvasRenderer])

const props = defineProps({ option: Function, height: { type: Number, default: 240 } })
const el = ref()
let chart, resizeObserver, scheme

function theme() {
  const css = getComputedStyle(document.documentElement)
  const v = (name) => css.getPropertyValue(name).trim()
  return {
    series: v('--series'), accent: v('--accent'), ink: v('--ink'), ink2: v('--ink-2'),
    muted: v('--muted'), line: v('--line'), surface: v('--surface'),
    axis: {
      axisLine: { lineStyle: { color: v('--line') } },
      axisTick: { show: false },
      axisLabel: { color: v('--muted'), fontSize: 11 },
      splitLine: { lineStyle: { color: v('--line'), width: 1 } },
    },
    tooltip: {
      backgroundColor: v('--surface'), borderColor: v('--line'),
      textStyle: { color: v('--ink'), fontSize: 13 },
    },
  }
}

const render = () => chart?.setOption(props.option(theme()), true)

onMounted(() => {
  chart = echarts.init(el.value)
  render()
  resizeObserver = new ResizeObserver(() => chart.resize())
  resizeObserver.observe(el.value)
  scheme = matchMedia('(prefers-color-scheme: dark)')
  scheme.addEventListener('change', render)
})
onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  scheme?.removeEventListener('change', render)
  chart?.dispose()
})
watch(() => props.option, render)
</script>

<template>
  <div ref="el" :style="{ height: height + 'px' }"></div>
</template>
