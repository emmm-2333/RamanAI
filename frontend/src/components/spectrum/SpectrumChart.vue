<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { useDark } from '@vueuse/core'
import { useTranslations } from '../../composables/useTranslations'

const props = defineProps({
  /** { x: number[], y: number[] } */
  spectralData: { type: Object, default: null },
  /** 'Malignant' | 'Benign' | null */
  diagnosis: { type: String, default: null },
  confidence: { type: Number, default: null },
})

const isDark = useDark()
const { translateDiagnosis } = useTranslations()
const chartContainer = ref(null)
let myChart = null

const diagnosisColor = () =>
  props.diagnosis === 'Malignant' ? '#FF0000' : '#28a745'

const buildBaseOption = () => ({
  backgroundColor: 'transparent',
  title: {
    text: '拉曼光谱分析趋势图',
    left: '20px',
    top: '20px',
    textStyle: {
      fontSize: 18,
      fontWeight: 'normal',
      color: isDark.value ? '#ccc' : '#333',
    },
  },
  tooltip: { trigger: 'axis' },
  grid: { left: '3%', right: '4%', bottom: '3%', top: '80px', containLabel: true },
  toolbox: {
    feature: {
      saveAsImage: { title: '保存图片' },
      dataZoom: { title: { zoom: '区域缩放', back: '还原' } },
      restore: { title: '重置' },
    },
    top: '20px',
    right: '20px',
  },
  xAxis: {
    type: 'category',
    name: 'Wavenumber (cm⁻¹)',
    nameLocation: 'middle',
    nameGap: 30,
    boundaryGap: false,
    data: Array.from({ length: 1801 }, (_, i) => i + 400),
    axisLine: { lineStyle: { color: isDark.value ? '#666' : '#999' } },
  },
  yAxis: {
    type: 'value',
    name: 'Intensity (a.u.)',
    axisLine: { show: true, lineStyle: { color: isDark.value ? '#666' : '#999' } },
    splitLine: { lineStyle: { type: 'dashed', color: isDark.value ? '#444' : '#eee' } },
  },
  series: [{ name: '原始光谱', type: 'line', data: [], smooth: true, showSymbol: false,
    itemStyle: { color: '#0072C6' },
    areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
      { offset: 0, color: 'rgba(0, 114, 198, 0.3)' },
      { offset: 1, color: 'rgba(0, 114, 198, 0.05)' },
    ]) },
  }],
  dataZoom: [{ type: 'inside' }, { type: 'slider' }],
})

const initChart = () => {
  if (!chartContainer.value) return
  myChart = echarts.init(chartContainer.value, isDark.value ? 'dark' : undefined)
  myChart.setOption(buildBaseOption())
  if (props.spectralData) applyData()
}

const applyData = () => {
  if (!myChart || !props.spectralData) return
  const { x, y } = props.spectralData
  const color = diagnosisColor()
  const xData = x?.length ? [...x] : Array.from({ length: y.length }, (_, i) => i + 400)

  const titleText = props.diagnosis && props.confidence != null
    ? `诊断结果: ${translateDiagnosis(props.diagnosis)} (置信度: ${(props.confidence * 100).toFixed(2)}%)`
    : '拉曼光谱分析趋势图'

  myChart.setOption({
    title: { text: titleText, textStyle: { color, fontWeight: 'bold' } },
    xAxis: { data: xData },
    series: [{
      data: [...y],
      itemStyle: { color },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: props.diagnosis === 'Malignant' ? 'rgba(255,0,0,0.3)' : 'rgba(40,167,69,0.3)' },
        { offset: 1, color: props.diagnosis === 'Malignant' ? 'rgba(255,0,0,0.05)' : 'rgba(40,167,69,0.05)' },
      ]) },
    }],
  })
}

watch(() => props.spectralData, applyData)
watch(() => props.diagnosis,    applyData)
watch(isDark, () => { myChart?.dispose(); initChart() })

const onResize = () => myChart?.resize()

onMounted(() => {
  initChart()
  window.addEventListener('resize', onResize)
})
onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  myChart?.dispose()
})
</script>

<template>
  <div ref="chartContainer" class="w-full h-full min-h-[500px]" />
</template>
