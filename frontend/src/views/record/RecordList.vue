<script setup>
import { ref, onMounted } from 'vue';
import spectrumApi from '../../api/spectrum';
import { useRouter } from 'vue-router';
import { Search, Refresh, View, Download, Upload } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';

const handleExport = async () => {
    // Basic CSV export of current list metadata
    const rows = [['ID', 'Patient Name', 'Diagnosis', 'Confidence', 'Created At']];
    records.value.forEach(r => {
        rows.push([
            r.id,
            r.patient_name || 'Anonymous',
            r.diagnosis_result,
            r.confidence_score,
            r.created_at
        ]);
    });
    
    let csvContent = "data:text/csv;charset=utf-8," 
        + rows.map(e => e.join(",")).join("\n");
        
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "raman_records.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
};

const router = useRouter();
const loading = ref(false);
const records = ref([]);
const total = ref(0);
const queryParams = ref({
  page: 1,
  page_size: 10,
  search: '',
  diagnosis: ''
});

// Batch Import
const batchImportDialogVisible = ref(false);
const isBatchUploading = ref(false);
const batchFileList = ref([]);

const handleBatchUpload = async () => {
  if (batchFileList.value.length === 0) {
    ElMessage.warning('请选择文件');
    return;
  }
  
  isBatchUploading.value = true;
  const formData = new FormData();
  formData.append('file', batchFileList.value[0].raw);
  
  try {
    const res = await spectrumApi.batchUploadSpectrum(formData);
    ElMessage.success(`导入成功: ${res.data.imported} 条记录`);
    if (res.data.errors && res.data.errors.length > 0) {
       ElMessage.warning(`部分失败: ${res.data.errors.length} 条，请查看控制台`);
       console.warn('Import errors:', res.data.errors);
    }
    batchImportDialogVisible.value = false;
    batchFileList.value = [];
    fetchRecords();
  } catch (error) {
    ElMessage.error('批量导入失败');
    console.error(error);
  } finally {
    isBatchUploading.value = false;
  }
};

const fetchRecords = async () => {
  loading.value = true;
  try {
    // Currently backend UploadView is POST only.
    // We assume backend has a List API now. If not, this will fail.
    // But per task plan, we should implement frontend first.
    // We might need to mock or ensure backend supports it.
    // Let's assume backend /api/v1/upload/ supports GET or similar.
    // Actually, based on previous tool outputs, UploadView is APIView with only POST.
    // We should probably add a GET method to UploadView or a separate View in backend later.
    // For now, let's implement the frontend logic.
    const res = await spectrumApi.getRecords(queryParams.value);
    records.value = res.data.results || [];
    total.value = res.data.count || 0;
  } catch (error) {
    console.error(error);
  } finally {
    loading.value = false;
  }
};

const handleSearch = () => {
  queryParams.value.page = 1;
  fetchRecords();
};

const handleView = (row) => {
  router.push(`/records/${row.id}`);
};

onMounted(() => {
  fetchRecords();
});
</script>

<template>
  <div class="p-6 h-full flex flex-col">
    <div class="mb-4 flex justify-between items-center">
      <h2 class="text-xl font-bold text-gray-800 dark:text-white">光谱记录管理</h2>
      <div class="flex gap-2">
        <el-input
          v-model="queryParams.search"
          placeholder="搜索患者姓名/ID"
          prefix-icon="Search"
          class="!w-64"
          @keyup.enter="handleSearch"
        />
        <el-select v-model="queryParams.diagnosis" placeholder="诊断结果" clearable class="!w-40">
          <el-option label="良性 (Benign)" value="Benign" />
          <el-option label="恶性 (Malignant)" value="Malignant" />
        </el-select>
        <el-button type="primary" @click="handleSearch">查询</el-button>
        <el-button type="success" :icon="Download" @click="handleExport">导出 CSV</el-button>
        <el-button type="warning" :icon="Upload" @click="batchImportDialogVisible = true">批量导入</el-button>
      </div>
    </div>

    <div class="flex-1 bg-white dark:bg-gray-800 rounded-lg shadow p-4 overflow-hidden">
      <el-table :data="records" v-loading="loading" height="100%" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="patient_name" label="患者姓名/ID" width="150" />
        <el-table-column prop="diagnosis_result" label="诊断结果">
          <template #default="{ row }">
            <el-tag :type="row.diagnosis_result === 'Malignant' ? 'danger' : 'success'">
              {{ row.diagnosis_result }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="confidence_score" label="置信度">
          <template #default="{ row }">
            {{ (row.confidence_score * 100).toFixed(2) }}%
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="上传时间" width="180">
            <template #default="{ row }">
                {{ new Date(row.created_at).toLocaleString() }}
            </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :icon="View" @click="handleView(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="mt-4 flex justify-end">
      <el-pagination
        v-model:current-page="queryParams.page"
        v-model:page-size="queryParams.page_size"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="fetchRecords"
      />
    </div>

    <!-- Batch Import Dialog -->
    <el-dialog v-model="batchImportDialogVisible" title="批量导入数据集" width="400px">
      <div class="flex flex-col gap-4">
        <el-alert title="支持格式：.zip (多个文件) 或 .xlsx (宽表格式)" type="info" :closable="false" />
        <el-upload
          class="w-full"
          drag
          action="#"
          :auto-upload="false"
          :file-list="batchFileList"
          :limit="1"
          :on-change="(file) => batchFileList = [file]"
          :on-remove="() => batchFileList = []"
        >
          <el-icon class="el-icon--upload"><Upload /></el-icon>
          <div class="el-upload__text">
            拖拽文件至此 或 <em>点击上传</em>
          </div>
        </el-upload>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="batchImportDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleBatchUpload" :loading="isBatchUploading">开始导入</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>
