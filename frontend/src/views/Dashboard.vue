<script setup>
import { ref, onMounted, onUnmounted, watch } from "vue";
import { useAuthStore } from "../stores/auth";
import * as echarts from "echarts";
import { useDark } from "@vueuse/core";
import spectrumApi from "../api/spectrum";
import { ElMessage } from "element-plus";
import {
  Upload,
  User,
  Monitor,
  Loading,
  UploadFilled
} from "@element-plus/icons-vue";

const authStore = useAuthStore();
const isDark = useDark();

const chartContainer = ref(null);
let myChart = null;

// 上传相关
const fileList = ref([]);
const patientId = ref("");
const isUploading = ref(false);

// 诊断结果
const diagnosisResult = ref(null);

// 初始化图表
const initChart = () => {
  if (!chartContainer.value) return;

  // 根据当前主题初始化
  myChart = echarts.init(
    chartContainer.value,
    isDark.value ? "dark" : undefined,
  );

  const option = {
    backgroundColor: "transparent",
    title: {
      text: "拉曼光谱分析趋势图",
      left: "20px",
      top: "20px",
      textStyle: {
        fontSize: 18,
        fontWeight: "normal",
        color: isDark.value ? "#ccc" : "#333",
      },
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(255, 255, 255, 0.9)",
      borderColor: "#ccc",
      textStyle: {
        color: "#333",
      },
    },
    grid: {
      left: "3%",
      right: "4%",
      bottom: "3%",
      top: "80px",
      containLabel: true,
    },
    toolbox: {
      feature: {
        saveAsImage: { title: "保存图片" },
        dataZoom: { title: { zoom: "区域缩放", back: "还原" } },
        restore: { title: "重置" },
      },
      top: "20px",
      right: "20px",
    },
    xAxis: {
      type: "category",
      name: "Wavenumber (cm⁻¹)",
      nameLocation: "middle",
      nameGap: 30,
      boundaryGap: false,
      data: Array.from({ length: 1801 }, (_, i) => i + 400),
      axisLine: { lineStyle: { color: isDark.value ? "#666" : "#999" } },
    },
    yAxis: {
      type: "value",
      name: "Intensity (a.u.)",
      axisLine: {
        show: true,
        lineStyle: { color: isDark.value ? "#666" : "#999" },
      },
      splitLine: {
        lineStyle: { type: "dashed", color: isDark.value ? "#444" : "#eee" },
      },
    },
    series: [
      {
        name: "原始光谱",
        type: "line",
        data: [],
        smooth: true,
        showSymbol: false,
        itemStyle: { color: "#0072C6" },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(0, 114, 198, 0.3)" },
            { offset: 1, color: "rgba(0, 114, 198, 0.05)" },
          ]),
        },
      },
    ],
    dataZoom: [{ type: "inside" }, { type: "slider" }],
  };

  myChart.setOption(option);
};

// 监听主题变化更新图表
watch(isDark, () => {
  if (myChart) {
    myChart.dispose();
    initChart();
  }
});

onMounted(() => {
  initChart();
  window.addEventListener("resize", () => myChart?.resize());
});

onUnmounted(() => {
  window.removeEventListener("resize", () => myChart?.resize());
  myChart?.dispose();
});

// 处理文件上传
const handleUpload = async (file) => {
  isUploading.value = true;
  const formData = new FormData();
  formData.append("file", file.raw);
  if (patientId.value) {
    formData.append("patient_id", patientId.value);
  }

  try {
    const response = await spectrumApi.uploadSpectrum(formData);
    diagnosisResult.value = response.data;
    ElMessage.success("诊断完成");
    updateChartWithResult(response.data);
  } catch (error) {
    // Error handled by interceptor or here
    if (!error.response || error.response.status !== 401) {
       // Display specific error from backend if available
       const errorMsg = error.response?.data?.error || "上传失败";
       ElMessage.error(errorMsg);
    }
    console.error(error);
  } finally {
    isUploading.value = false;
    fileList.value = [];
  }
};

const updateChartWithResult = (result) => {
  if (!myChart) return;
  const isMalignant = result.diagnosis_result === "Malignant";
  const color = isMalignant ? "#FF0000" : "#28a745";

  // 获取真实数据
  const spectralData = result.spectral_data;
  const xData = spectralData ? spectralData.x : [];
  const yData = spectralData ? spectralData.y : [];

  // If xData is just indices (0, 1, 2...) or default range, we display it.
  // Backend now ensures xData is 400-2200 for standard files.
  
  // Create a copy of xData to avoid reactivity issues with ECharts
  let finalXData = [];
  if (xData && xData.length > 0) {
      finalXData = [...xData];
  } else {
      // Fallback generation
      const len = (yData && yData.length > 0) ? yData.length : 1801;
      finalXData = Array.from({ length: len }, (_, i) => i + 400);
  }

  // Deep copy yData as well
  const finalYData = yData ? [...yData] : [];

  const option = {
    title: {
      text: `诊断结果: ${result.diagnosis_result} (置信度: ${(result.confidence_score * 100).toFixed(2)}%)`,
      textStyle: { color: color, fontWeight: "bold" },
    },
    xAxis: {
        data: finalXData
    },
    series: [
      {
        data: finalYData,
        itemStyle: { color: color },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            {
              offset: 0,
              color: isMalignant
                ? "rgba(255, 0, 0, 0.3)"
                : "rgba(40, 167, 69, 0.3)",
            },
            {
              offset: 1,
              color: isMalignant
                ? "rgba(255, 0, 0, 0.05)"
                : "rgba(40, 167, 69, 0.05)",
            },
          ]),
        },
      },
    ],
  };

  // Use notMerge=true to force complete refresh
  myChart.setOption(option);
};
</script>

<template>
  <div class="h-full flex flex-col md:flex-row overflow-hidden">
    <!-- Sidebar -->
    <div
      class="w-full md:w-[320px] p-6 overflow-y-auto border-b md:border-b-0 md:border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
    >
      <!-- 病患信息卡片 -->
      <div class="mb-6">
        <div
          class="flex items-center gap-2 mb-4 pb-2 border-b border-gray-100 dark:border-gray-700"
        >
          <el-icon class="text-medical-primary"><User /></el-icon>
          <span class="font-semibold text-gray-800 dark:text-gray-200"
            >患者信息</span
          >
        </div>
        <el-form label-position="top">
          <el-form-item label="患者 ID / 编号" class="!mb-0">
            <el-input
              v-model="patientId"
              placeholder="输入 ID (如: P-2026001)"
              size="large"
              :prefix-icon="Monitor"
              class="!w-full"
            />
          </el-form-item>
        </el-form>
      </div>

      <!-- 操作卡片 -->
      <div class="mb-6">
        <div
          class="flex items-center gap-2 mb-4 pb-2 border-b border-gray-100 dark:border-gray-700"
        >
          <el-icon class="text-medical-primary"><Upload /></el-icon>
          <span class="font-semibold text-gray-800 dark:text-gray-200"
            >光谱数据录入</span
          >
        </div>
        <div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-1">
          <el-upload
            class="w-full"
            drag
            action="#"
            :auto-upload="false"
            :on-change="handleUpload"
            :file-list="fileList"
            :limit="1"
            :show-file-list="false"
          >
            <el-icon class="el-icon--upload !text-medical-primary"
              ><UploadFilled
            /></el-icon>
            <div class="el-upload__text dark:text-gray-300">
              拖拽文件至此 或 <em class="text-medical-primary">点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip text-center dark:text-gray-400">
                支持 .txt / .csv / .xlsx 格式，最大 30MB
              </div>
            </template>
          </el-upload>

          <div
            v-if="isUploading"
            class="text-center py-3 text-medical-primary flex items-center justify-center gap-2"
          >
            <el-icon class="is-loading"><Loading /></el-icon>
            <span class="text-sm font-medium">正在分析数据...</span>
          </div>
        </div>
      </div>

      <!-- 诊断结果卡片 -->
      <transition name="el-fade-in">
        <div
          v-if="diagnosisResult"
          class="rounded-lg border-l-4 p-4 shadow-sm transition-all duration-300 bg-white dark:bg-gray-700/50"
          :class="
            diagnosisResult.diagnosis_result === 'Malignant'
              ? 'border-medical-danger bg-red-50 dark:bg-red-900/10'
              : 'border-medical-success bg-green-50 dark:bg-green-900/10'
          "
        >
          <div class="flex justify-between items-center mb-4">
            <span class="font-bold text-gray-800 dark:text-gray-100"
              >智能诊断报告</span
            >
            <el-tag
              :type="
                diagnosisResult.diagnosis_result === 'Malignant'
                  ? 'danger'
                  : 'success'
              "
              effect="dark"
              round
            >
              {{
                diagnosisResult.diagnosis_result === "Malignant"
                  ? "高风险"
                  : "低风险"
              }}
            </el-tag>
          </div>
          <div class="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label
                class="block text-xs text-gray-500 dark:text-gray-400 mb-1"
                >诊断类型</label
              >
              <span
                class="text-lg font-medium text-gray-800 dark:text-gray-200"
                >{{ diagnosisResult.diagnosis_result }}</span
              >
            </div>
            <div>
              <label
                class="block text-xs text-gray-500 dark:text-gray-400 mb-1"
                >AI 置信度</label
              >
              <span
                class="text-lg font-medium text-gray-800 dark:text-gray-200"
                >{{
                  (diagnosisResult.confidence_score * 100).toFixed(2)
                }}%</span
              >
            </div>
          </div>
          <div v-if="diagnosisResult.diagnosis_result === 'Malignant'">
            <el-alert
              title="检测到异常，建议立即复核"
              type="error"
              show-icon
              :closable="false"
              class="!bg-white/80 dark:!bg-gray-800/80"
            />
          </div>
        </div>
      </transition>
    </div>

    <!-- Main Content -->
    <div class="flex-1 p-6 bg-gray-50 dark:bg-gray-900 overflow-hidden">
      <div
        class="h-full bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-1 flex flex-col"
      >
        <div ref="chartContainer" class="flex-1 w-full min-h-[500px]"></div>
      </div>
    </div>
  </div>
</template>
