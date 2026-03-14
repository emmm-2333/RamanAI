<script setup>
import { useTranslations } from '../../composables/useTranslations'

/** result: SpectrumRecord 对象（来自 API） */
defineProps({
  result: { type: Object, required: true },
})

const { translateMarker, translateStatus, translateDiagnosis } = useTranslations()
</script>

<template>
  <div
    class="rounded-lg border-l-4 p-4 shadow-sm transition-all duration-300 bg-white dark:bg-gray-700/50"
    :class="result.diagnosis_result === 'Malignant'
      ? 'border-medical-danger bg-red-50 dark:bg-red-900/10'
      : 'border-medical-success bg-green-50 dark:bg-green-900/10'"
  >
    <div class="flex justify-between items-center mb-4">
      <span class="font-bold text-gray-800 dark:text-gray-100">智能诊断报告</span>
      <el-tag
        :type="result.diagnosis_result === 'Malignant' ? 'danger' : 'success'"
        effect="dark" round
      >
        {{ result.diagnosis_result === 'Malignant' ? '高风险' : '低风险' }}
      </el-tag>
    </div>

    <div class="grid grid-cols-2 gap-4 mb-4">
      <div>
        <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">诊断类型</label>
        <span class="text-lg font-medium text-gray-800 dark:text-gray-200">
          {{ translateDiagnosis(result.diagnosis_result) }}
        </span>
      </div>
      <div>
        <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">AI 置信度</label>
        <span class="text-lg font-medium text-gray-800 dark:text-gray-200">
          {{ (result.confidence_score * 100).toFixed(2) }}%
        </span>
      </div>
    </div>

    <!-- 分子分型预测 -->
    <div
      v-if="result.metadata?.predicted_markers"
      class="mb-4 pt-4 border-t border-gray-200 dark:border-gray-600"
    >
      <div class="font-semibold text-gray-800 dark:text-gray-200 mb-3 text-sm">分子分型预测</div>
      <div class="grid grid-cols-2 gap-3">
        <div
          v-for="(markerStatus, marker) in result.metadata.predicted_markers"
          :key="marker"
          class="flex justify-between items-center bg-white dark:bg-gray-800 p-2 rounded border border-gray-100 dark:border-gray-600"
        >
          <span class="text-xs font-bold text-gray-600 dark:text-gray-400">
            {{ translateMarker(marker) }}
          </span>
          <el-tag
            size="small"
            :type="markerStatus === 'Positive' || markerStatus === 'High' ? 'danger' : 'info'"
            effect="plain"
          >
            {{ translateStatus(markerStatus) }}
          </el-tag>
        </div>
      </div>
    </div>

    <div v-if="result.diagnosis_result === 'Malignant'">
      <el-alert
        title="检测到异常，建议立即复核"
        type="error"
        show-icon
        :closable="false"
        class="!bg-white/80 dark:!bg-gray-800/80"
      />
    </div>
  </div>
</template>
