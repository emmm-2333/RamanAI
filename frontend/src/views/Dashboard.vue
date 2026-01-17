<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'
import ThemeToggle from '../components/ThemeToggle.vue'
import * as echarts from 'echarts'
import { useDark } from '@vueuse/core'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const authStore = useAuthStore()
const router = useRouter()
const isDark = useDark()

const chartContainer = ref(null)
let myChart = null

// 上传相关
const fileList = ref([])
const patientId = ref('')
const isUploading = ref(false)

// 诊断结果
const diagnosisResult = ref(null)

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}

// 初始化图表
const initChart = () => {
  if (!chartContainer.value) return
  
  // 根据当前主题初始化
  myChart = echarts.init(chartContainer.value, isDark.value ? 'dark' : undefined)
  
  const option = {
    backgroundColor: 'transparent',
    title: {
      text: '拉曼光谱分析',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    toolbox: {
      feature: {
        saveAsImage: {}
      }
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: Array.from({length: 100}, (_, i) => i + 400) // 模拟波长 400-500
    },
    yAxis: {
      type: 'value',
      name: 'Intensity'
    },
    series: [
      {
        name: '原始光谱',
        type: 'line',
        data: Array.from({length: 100}, () => Math.random() * 1000), // 初始随机数据
        smooth: true
      }
    ],
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: 0,
        filterMode: 'filter'
      },
      {
        type: 'slider',
        xAxisIndex: 0,
        filterMode: 'filter'
      }
    ]
  }
  
  myChart.setOption(option)
}

// 监听主题变化更新图表
watch(isDark, () => {
  if (myChart) {
    myChart.dispose()
    initChart()
  }
})

onMounted(() => {
  initChart()
  window.addEventListener('resize', () => myChart?.resize())
})

onUnmounted(() => {
  window.removeEventListener('resize', () => myChart?.resize())
  myChart?.dispose()
})

// 处理文件上传
const handleUpload = async (file) => {
  isUploading.value = true
  const formData = new FormData()
  formData.append('file', file.raw)
  if (patientId.value) {
    formData.append('patient_id', patientId.value)
  }
  
  try {
    const token = localStorage.getItem('access_token')
    const response = await axios.post('http://127.0.0.1:8000/api/v1/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
        'Authorization': `Bearer ${token}`
      }
    })
    
    diagnosisResult.value = response.data
    ElMessage.success('诊断完成')
    
    // TODO: 使用返回的实际数据更新图表
    // 这里仅模拟更新
    updateChartWithResult(response.data)
    
  } catch (error) {
    ElMessage.error('上传失败')
    console.error(error)
  } finally {
    isUploading.value = false
    // 清除文件列表，允许再次上传
    fileList.value = []
  }
}

const updateChartWithResult = (result) => {
  if (!myChart) return
  // 模拟根据诊断结果生成新的曲线
  const newData = Array.from({length: 100}, () => Math.random() * 1000 + (result.diagnosis_result === 'Malignant' ? 500 : 0))
  
  myChart.setOption({
    title: {
      text: `诊断结果: ${result.diagnosis_result} (置信度: ${result.confidence_score})`,
      textStyle: {
        color: result.diagnosis_result === 'Malignant' ? '#F56C6C' : '#67C23A'
      }
    },
    series: [{
      data: newData
    }]
  })
}
</script>

<template>
  <el-container class="layout-container">
    <el-header class="header">
      <div class="logo">
        RamanAI
      </div>
      <div class="user-info">
        <span class="username" v-if="authStore.user">
          欢迎, {{ authStore.user.username }} ({{ authStore.user.role }})
        </span>
        <ThemeToggle />
        <el-button type="danger" link @click="handleLogout" style="margin-left: 15px;">退出</el-button>
      </div>
    </el-header>
    
    <el-container>
      <el-aside width="300px" class="aside">
        <el-card class="control-panel">
          <template #header>
            <div class="card-header">
              <span>操作面板</span>
            </div>
          </template>
          
          <el-form label-position="top">
            <el-form-item label="病人 ID (可选)">
              <el-input v-model="patientId" placeholder="请输入病人ID" />
            </el-form-item>
            
            <el-form-item label="上传光谱文件 (.txt/.csv)">
              <el-upload
                class="upload-demo"
                action="#"
                :auto-upload="false"
                :on-change="handleUpload"
                :file-list="fileList"
                :limit="1"
                :show-file-list="false"
              >
                <el-button type="primary" :loading="isUploading">选择文件并诊断</el-button>
              </el-upload>
            </el-form-item>
          </el-form>
          
          <div v-if="diagnosisResult" class="result-box" :class="diagnosisResult.diagnosis_result">
            <h3>诊断结果</h3>
            <p><strong>类型:</strong> {{ diagnosisResult.diagnosis_result }}</p>
            <p><strong>置信度:</strong> {{ diagnosisResult.confidence_score }}</p>
          </div>
        </el-card>
      </el-aside>
      
      <el-main class="main">
        <div ref="chartContainer" class="chart-container"></div>
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout-container {
  height: 100vh;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--el-border-color);
  padding: 0 20px;
}

.logo {
  font-size: 1.5rem;
  font-weight: bold;
  color: var(--el-color-primary);
}

.user-info {
  display: flex;
  align-items: center;
}

.username {
  margin-right: 15px;
  font-size: 0.9rem;
}

.aside {
  border-right: 1px solid var(--el-border-color);
  padding: 20px;
}

.main {
  padding: 20px;
  background-color: var(--el-bg-color-page);
}

.chart-container {
  width: 100%;
  height: 100%;
  min-height: 500px;
  background-color: var(--el-bg-color);
  border-radius: 4px;
}

.result-box {
  margin-top: 20px;
  padding: 15px;
  border-radius: 4px;
  background-color: var(--el-fill-color-light);
}

.result-box.Malignant {
  border-left: 5px solid #F56C6C;
  background-color: rgba(245, 108, 108, 0.1);
}

.result-box.Benign {
  border-left: 5px solid #67C23A;
  background-color: rgba(103, 194, 58, 0.1);
}
</style>
