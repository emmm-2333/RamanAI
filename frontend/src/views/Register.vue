<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { ElMessage } from 'element-plus'
import { User, Lock, Message } from '@element-plus/icons-vue'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  email: ''
})

const loading = ref(false)

const handleRegister = async () => {
  if (!form.username || !form.password || !form.email) {
    ElMessage.warning('请填写完整信息')
    return
  }
  
  if (form.password !== form.confirmPassword) {
    ElMessage.warning('两次密码输入不一致')
    return
  }

  loading.value = true
  try {
    await authStore.register(form.username, form.password, form.email)
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (error) {
    // 更好的错误处理，显示后端返回的具体错误信息
    if (error.username) {
        ElMessage.error(`注册失败：${error.username[0]}`)
    } else if (error.password) {
        ElMessage.error(`注册失败：${error.password[0]}`)
    } else if (error.email) {
        ElMessage.error(`注册失败：${error.email[0]}`)
    } else {
        ElMessage.error('注册失败，请检查网络或联系管理员')
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="register-container">
    <el-card class="register-card">
      <template #header>
        <div class="card-header">
          <h2>注册账号</h2>
        </div>
      </template>
      
      <el-form :model="form" @submit.prevent="handleRegister">
        <el-form-item>
          <el-input 
            v-model="form.username" 
            placeholder="用户名" 
            :prefix-icon="User"
            size="large"
          />
        </el-form-item>
        
        <el-form-item>
          <el-input 
            v-model="form.email" 
            placeholder="邮箱" 
            :prefix-icon="Message"
            size="large"
          />
        </el-form-item>
        
        <el-form-item>
          <el-input 
            v-model="form.password" 
            type="password" 
            placeholder="密码" 
            :prefix-icon="Lock"
            show-password
            size="large"
          />
        </el-form-item>
        
        <el-form-item>
          <el-input 
            v-model="form.confirmPassword" 
            type="password" 
            placeholder="确认密码" 
            :prefix-icon="Lock"
            show-password
            size="large"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button 
            type="primary" 
            native-type="submit" 
            :loading="loading" 
            class="full-width"
            size="large"
          >
            注册
          </el-button>
        </el-form-item>
        
        <div class="actions">
          <router-link to="/login">已有账号？去登录</router-link>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: var(--el-bg-color-page);
}

.register-card {
  width: 400px;
}

.card-header h2 {
  margin: 0;
  text-align: center;
  color: var(--el-color-primary);
}

.full-width {
  width: 100%;
}

.actions {
  text-align: center;
  margin-top: 10px;
}

.actions a {
  color: var(--el-color-primary);
  text-decoration: none;
}
</style>
