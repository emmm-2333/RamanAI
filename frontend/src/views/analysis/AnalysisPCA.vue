<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue';
import analysisApi from '../../api/analysis';
import * as echarts from 'echarts';
import { useDark } from '@vueuse/core';
import { ElMessage } from 'element-plus';

const isDark = useDark();
const loading = ref(false);
const chartContainer = ref(null);
let myChart = null;

const initChart = (data) => {
  if (!chartContainer.value || !data) return;
  
  myChart = echarts.init(chartContainer.value, isDark.value ? 'dark' : undefined);
  
  // Group data by category
  const benignData = data.filter(item => item.category !== 'Malignant').map(item => [item.x, item.y]);
  const malignantData = data.filter(item => item.category === 'Malignant').map(item => [item.x, item.y]);

  const option = {
    backgroundColor: 'transparent',
    title: {
      text: 'PCA 降维分布图',
      left: 'center'
    },
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
         return `${params.seriesName}<br/>PC1: ${params.value[0].toFixed(2)}<br/>PC2: ${params.value[1].toFixed(2)}`;
      }
    },
    legend: {
      data: ['良性 (Benign)', '恶性 (Malignant)'],
      bottom: 10
    },
    xAxis: { name: 'PC1', scale: true },
    yAxis: { name: 'PC2', scale: true },
    series: [
      {
        name: '良性 (Benign)',
        type: 'scatter',
        symbolSize: 10,
        data: benignData,
        itemStyle: { color: '#28a745', opacity: 0.7 }
      },
      {
        name: '恶性 (Malignant)',
        type: 'scatter',
        symbolSize: 10,
        data: malignantData,
        itemStyle: { color: '#dc3545', opacity: 0.7 }
      }
    ]
  };
  
  myChart.setOption(option);
};

const fetchData = async () => {
  loading.value = true;
  try {
    const res = await analysisApi.getPCAData();
    initChart(res.data.data);
  } catch (error) {
    console.error(error);
    ElMessage.error('无法获取分析数据，请稍后重试');
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchData();
  window.addEventListener('resize', () => myChart?.resize());
});

onUnmounted(() => {
  window.removeEventListener('resize', () => myChart?.resize());
  myChart?.dispose();
});

watch(isDark, () => {
  if (myChart) {
    const opt = myChart.getOption();
    myChart.dispose();
    myChart = echarts.init(chartContainer.value, isDark.value ? 'dark' : undefined);
    myChart.setOption(opt);
  }
});
</script>

<template>
  <div class="p-6 h-full flex flex-col">
    <div class="mb-4">
      <h2 class="text-xl font-bold text-gray-800 dark:text-white">高级数据分析</h2>
      <p class="text-sm text-gray-500 mt-1">基于主成分分析 (PCA) 的样本分布可视化，展示良恶性样本在低维空间的聚集情况。</p>
    </div>

    <div class="flex-1 bg-white dark:bg-gray-800 rounded-lg shadow p-4 relative" v-loading="loading">
      <div ref="chartContainer" class="w-full h-full min-h-[500px]"></div>
    </div>
  </div>
</template>
