<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import spectrumApi from '../../api/spectrum';
import * as echarts from 'echarts';
import { useDark } from '@vueuse/core';
import { ArrowLeft } from '@element-plus/icons-vue';

const route = useRoute();
const router = useRouter();
const isDark = useDark();
const loading = ref(false);
const record = ref(null);
const chartContainer = ref(null);
let myChart = null;

const preprocessConfig = ref({
  smooth: true,
  baseline: true,
  normalize: true,
  baseline_method: 'poly',
  normalize_method: 'minmax',
  derivative: 0
});

const applyPreprocessing = async () => {
  if (!record.value) return;
  loading.value = true;
  try {
    const res = await spectrumApi.preprocessRecord(record.value.id, preprocessConfig.value);
    const processedData = res.data;
    updateChartWithData(processedData.x, processedData.y);
  } catch (error) {
    console.error(error);
  } finally {
    loading.value = false;
  }
};

const initChart = () => {
  if (!chartContainer.value) return;
  myChart = echarts.init(chartContainer.value, isDark.value ? 'dark' : undefined);
  updateChart();
};

const updateChart = () => {
  
  const spectralData = record.value.spectral_data || { x: [], y: [] };
  const isMalignant = record.value.diagnosis_result === 'Malignant';
  const color = isMalignant ? '#FF0000' : '#28a745';
  
  // Ensure we have data
  if (!spectralData.y || spectralData.y.length === 0) {
      console.warn("No spectral data to display");
      return;
  }
  
  const xData = spectralData.x && spectralData.x.length === spectralData.y.length 
      ? spectralData.x 
      : Array.from({length: spectralData.y.length}, (_, i) => i + 400);

  const option = {
    backgroundColor: 'transparent',
    title: {
      text: '光谱详情与对比',
      left: 'center'
    },
    tooltip: { trigger: 'axis' },
    legend: { data: ['当前样本'], bottom: 10 },
    xAxis: {
      type: 'category',
      data: xData,
      name: 'Wavenumber (cm⁻¹)',
      nameLocation: 'middle',
      nameGap: 30
    },
    yAxis: {
      type: 'value',
      name: 'Intensity'
    },
    series: [
      {
        name: '当前样本',
        type: 'line',
        data: spectralData.y,
        smooth: true,
        showSymbol: false,
        itemStyle: { color: color },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: isMalignant ? 'rgba(255, 0, 0, 0.3)' : 'rgba(40, 167, 69, 0.3)' },
            { offset: 1, color: isMalignant ? 'rgba(255, 0, 0, 0.05)' : 'rgba(40, 167, 69, 0.05)' }
          ])
        }
      }
    ]
  };
  myChart.setOption(option);
};

const updateChartWithData = (x, y) => {
  if (!myChart || !record.value) return;
  const isMalignant = record.value.diagnosis_result === 'Malignant';
  const color = isMalignant ? '#FF0000' : '#28a745';
  
  myChart.setOption({
    xAxis: {
      data: x.length ? x : Array.from({length: y.length}, (_, i) => i + 400)
    },
    series: [
      {
        name: '当前样本',
        data: y,
        itemStyle: { color: color }
      }
    ]
  });
};

const fetchRecord = async () => {
  loading.value = true;
  try {
    const res = await spectrumApi.getRecord(route.params.id);
    record.value = res.data;
    // Wait for DOM update
    setTimeout(() => {
        if (!myChart) initChart();
        else updateChart();
    }, 100);
  } catch (error) {
    console.error(error);
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchRecord();
  window.addEventListener('resize', () => myChart?.resize());
});

onUnmounted(() => {
  window.removeEventListener('resize', () => myChart?.resize());
  myChart?.dispose();
});

watch(isDark, () => {
  myChart?.dispose();
  initChart();
});
</script>

<template>
  <div class="p-6 h-full flex flex-col" v-loading="loading">
    <div class="mb-4">
      <el-page-header @back="router.back()" title="返回列表">
        <template #content>
          <span class="text-large font-600 mr-3"> 记录详情 #{{ route.params.id }} </span>
        </template>
      </el-page-header>
    </div>

    <div class="flex gap-4 h-full overflow-hidden" v-if="record">
      <!-- 左侧：基本信息 -->
      <div class="w-1/3 flex flex-col gap-4">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header font-bold">诊断结论</div>
          </template>
          <div class="flex flex-col items-center py-4">
            <el-tag
              :type="record.diagnosis_result === 'Malignant' ? 'danger' : 'success'"
              class="text-2xl px-6 py-2 h-auto mb-4"
            >
              {{ record.diagnosis_result }}
            </el-tag>
            <div class="text-gray-500">
              置信度: <span class="font-bold text-gray-800 dark:text-gray-200">{{ (record.confidence_score * 100).toFixed(2) }}%</span>
            </div>
          </div>
        </el-card>

        <el-card shadow="hover" class="flex-1">
          <template #header>
            <div class="card-header font-bold">患者及元数据</div>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="患者姓名">{{ record.patient_name || 'Anonymous' }}</el-descriptions-item>
            <el-descriptions-item label="上传时间">{{ new Date(record.created_at).toLocaleString() }}</el-descriptions-item>
            <el-descriptions-item label="上传者">{{ record.uploaded_by_name }}</el-descriptions-item>
            <template v-if="record.metadata">
               <el-descriptions-item v-for="(val, key) in record.metadata" :key="key" :label="key">
                 {{ val }}
               </el-descriptions-item>
            </template>
          </el-descriptions>
        </el-card>
        
        <el-card shadow="hover">
          <template #header>
            <div class="card-header font-bold">实时预处理</div>
          </template>
          <el-form :model="preprocessConfig" label-width="100px" size="small">
             <el-form-item label="平滑处理">
                <el-switch v-model="preprocessConfig.smooth" />
             </el-form-item>
             <el-form-item label="基线校正">
                <el-switch v-model="preprocessConfig.baseline" />
             </el-form-item>
             <el-form-item label="基线算法" v-if="preprocessConfig.baseline">
                <el-select v-model="preprocessConfig.baseline_method">
                   <el-option label="多项式拟合" value="poly" />
                   <el-option label="ALS (去荧光)" value="als" />
                </el-select>
             </el-form-item>
             <el-form-item label="归一化">
                <el-switch v-model="preprocessConfig.normalize" />
             </el-form-item>
             <el-form-item label="归一化算法" v-if="preprocessConfig.normalize">
                <el-select v-model="preprocessConfig.normalize_method">
                   <el-option label="Min-Max (0-1)" value="minmax" />
                   <el-option label="SNV (标准正态)" value="snv" />
                </el-select>
             </el-form-item>
             <el-form-item label="导数光谱">
                <el-select v-model="preprocessConfig.derivative">
                   <el-option label="无" :value="0" />
                   <el-option label="一阶导数" :value="1" />
                   <el-option label="二阶导数" :value="2" />
                </el-select>
             </el-form-item>
             <el-button type="primary" class="w-full mt-2" @click="applyPreprocessing" :loading="loading">应用处理</el-button>
          </el-form>
        </el-card>
      </div>

      <!-- 右侧：图表 -->
      <div class="flex-1 bg-white dark:bg-gray-800 rounded-lg shadow p-4 flex flex-col">
        <div ref="chartContainer" class="flex-1 w-full min-h-[400px]"></div>
      </div>
    </div>
  </div>
</template>
