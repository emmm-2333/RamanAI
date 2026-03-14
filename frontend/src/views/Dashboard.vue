<script setup>
import { ref } from "vue";
import { useAuthStore } from "../stores/auth";
import spectrumApi from "../api/spectrum";
import { ElMessage } from "element-plus";
import { Upload, User, Monitor, Loading, UploadFilled } from "@element-plus/icons-vue";
import SpectrumChart from "../components/spectrum/SpectrumChart.vue";
import DiagnosisResultCard from "../components/spectrum/DiagnosisResultCard.vue";

const authStore = useAuthStore();

// 上传相关
const fileList = ref([]);
const patientId = ref("");
const isUploading = ref(false);

// 诊断结果
const diagnosisResult = ref(null);

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
  } catch (error) {
    if (!error.response || error.response.status !== 401) {
      const errorMsg = error.response?.data?.error || "上传失败";
      ElMessage.error(errorMsg);
    }
    console.error(error);
  } finally {
    isUploading.value = false;
    fileList.value = [];
  }
};
</script>

<template>
  <div class="h-full flex flex-col md:flex-row overflow-hidden">
    <!-- 左侧面板 -->
    <div
      class="w-full md:w-[320px] p-6 overflow-y-auto border-b md:border-b-0 md:border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
    >
      <!-- 病患信息 -->
      <div class="mb-6">
        <div class="flex items-center gap-2 mb-4 pb-2 border-b border-gray-100 dark:border-gray-700">
          <el-icon class="text-medical-primary"><User /></el-icon>
          <span class="font-semibold text-gray-800 dark:text-gray-200">患者信息</span>
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

      <!-- 光谱数据上传 -->
      <div class="mb-6">
        <div class="flex items-center gap-2 mb-4 pb-2 border-b border-gray-100 dark:border-gray-700">
          <el-icon class="text-medical-primary"><Upload /></el-icon>
          <span class="font-semibold text-gray-800 dark:text-gray-200">光谱数据录入</span>
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
            <el-icon class="el-icon--upload !text-medical-primary"><UploadFilled /></el-icon>
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
        <DiagnosisResultCard v-if="diagnosisResult" :result="diagnosisResult" />
      </transition>
    </div>

    <!-- 光谱图 -->
    <div class="flex-1 p-6 bg-gray-50 dark:bg-gray-900 overflow-hidden">
      <div
        class="h-full bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-1 flex flex-col"
      >
        <SpectrumChart
          :spectral-data="diagnosisResult?.spectral_data ?? null"
          :diagnosis="diagnosisResult?.diagnosis_result ?? null"
          :confidence="diagnosisResult?.confidence_score ?? null"
        />
      </div>
    </div>
  </div>
</template>
