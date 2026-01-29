<script setup>
import { ref, onMounted } from 'vue';
import modelApi from '../../api/model';
import { ElMessage, ElMessageBox } from 'element-plus';
import { VideoPlay, Check } from '@element-plus/icons-vue';

const loading = ref(false);
const models = ref([]);
const trainingDialogVisible = ref(false);
const trainForm = ref({
  description: '',
  algorithm: 'rf',
  test_size: 0.2,
  n_estimators: 100
});

const fetchModels = async () => {
  loading.value = true;
  try {
    const res = await modelApi.getModels();
    models.value = res.data.results || res.data; // ListCreateAPIView might return list directly if pagination off
  } catch (error) {
    console.error(error);
  } finally {
    loading.value = false;
  }
};

const handleTrain = async () => {
  if (!trainForm.value.description) {
    ElMessage.warning('请输入训练描述');
    return;
  }
  
  trainingDialogVisible.value = false;
  // Use a simpler loading mechanism or ensure ElMessage is imported correctly
  // ElMessage.loading is part of ElMessage in recent Element Plus
  const loadingInstance = ElMessage({
    type: 'info',
    message: '正在训练新模型，请稍候...',
    duration: 0,
    showClose: false
  });

  try {
    await modelApi.trainModel(trainForm.value);
    loadingInstance.close();
    ElMessage.success('训练完成，新模型已上线');
    fetchModels();
  } catch (error) {
    loadingInstance.close();
    ElMessage.error('训练失败: ' + (error.response?.data?.error || '未知错误'));
  }
};

onMounted(() => {
  fetchModels();
});
</script>

<template>
  <div class="p-6 h-full flex flex-col">
    <div class="mb-4 flex justify-between items-center">
      <h2 class="text-xl font-bold text-gray-800 dark:text-white">模型版本管理</h2>
      <el-button type="primary" :icon="VideoPlay" @click="trainingDialogVisible = true">触发新训练</el-button>
    </div>

    <div class="flex-1 bg-white dark:bg-gray-800 rounded-lg shadow p-4 overflow-hidden">
      <el-table :data="models" v-loading="loading" height="100%" stripe style="width: 100%">
        <el-table-column prop="version" label="版本号" width="180" sortable />
        <el-table-column prop="is_active" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" effect="dark">
              {{ row.is_active ? 'Active' : 'Inactive' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="accuracy" label="准确率" sortable>
          <template #default="{ row }">
            <span class="font-bold text-green-600">{{ (row.accuracy * 100).toFixed(2) }}%</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="created_at" label="创建时间" width="180" sortable>
            <template #default="{ row }">
                {{ new Date(row.created_at).toLocaleString() }}
            </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Training Dialog -->
    <el-dialog v-model="trainingDialogVisible" title="触发模型训练" width="40%">
      <el-form :model="trainForm" label-position="top">
        <el-form-item label="训练描述 / 备注">
          <el-input v-model="trainForm.description" type="textarea" placeholder="例如：增加 100 条新样本后的重训" />
        </el-form-item>
        <el-row :gutter="20">
           <el-col :span="12">
             <el-form-item label="算法模型">
               <el-select v-model="trainForm.algorithm" placeholder="Random Forest">
                 <el-option label="Random Forest" value="rf" />
                 <el-option label="SVM" value="svm" disabled />
                 <el-option label="XGBoost" value="xgb" disabled />
               </el-select>
             </el-form-item>
           </el-col>
           <el-col :span="12">
             <el-form-item label="测试集比例">
               <el-slider v-model="trainForm.test_size" :min="0.1" :max="0.5" :step="0.05" show-input />
             </el-form-item>
           </el-col>
        </el-row>
        <el-row :gutter="20">
           <el-col :span="12">
             <el-form-item label="树的数量 (n_estimators)">
               <el-input-number v-model="trainForm.n_estimators" :min="10" :max="500" :step="10" />
             </el-form-item>
           </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="trainingDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleTrain">开始训练</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>
