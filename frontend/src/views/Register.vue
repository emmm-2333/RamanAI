<script setup>
import { ref, reactive } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { ElMessage } from "element-plus";
import { User, Lock, Message, FirstAidKit } from "@element-plus/icons-vue";

const router = useRouter();
const authStore = useAuthStore();

const form = reactive({
  username: "",
  password: "",
  confirmPassword: "",
  email: "",
});

const loading = ref(false);

const handleRegister = async () => {
  if (!form.username || !form.password || !form.email) {
    ElMessage.warning("请填写完整信息");
    return;
  }

  if (form.password !== form.confirmPassword) {
    ElMessage.warning("两次密码输入不一致");
    return;
  }

  loading.value = true;
  try {
    await authStore.register(form.username, form.password, form.email);
    ElMessage.success("注册成功，请登录");
    router.push("/login");
  } catch (error) {
    // 更好的错误处理，显示后端返回的具体错误信息
    if (error.username) {
      ElMessage.error(`注册失败：${error.username[0]}`);
    } else if (error.password) {
      ElMessage.error(`注册失败：${error.password[0]}`);
    } else if (error.email) {
      ElMessage.error(`注册失败：${error.email[0]}`);
    } else {
      ElMessage.error("注册失败，请检查网络或联系管理员");
    }
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <div
    class="flex items-center justify-center min-h-screen bg-gradient-to-br from-gray-50 to-gray-200 dark:from-gray-900 dark:to-gray-800"
  >
    <div
      class="w-full max-w-lg p-10 bg-white rounded-xl shadow-lg border-t-4 border-medical-primary dark:bg-gray-800"
    >
      <div class="text-center mb-8">
        <el-icon class="text-medical-primary mb-2" :size="48">
          <FirstAidKit />
        </el-icon>
        <h2 class="text-2xl font-bold text-medical-primary mb-2">创建新账号</h2>
        <p class="text-sm text-gray-500 dark:text-gray-400">
          RamanAI 医疗平台 - 医生端
        </p>
      </div>

      <el-form
        :model="form"
        @submit.prevent="handleRegister"
        size="large"
        label-position="top"
      >
        <el-form-item>
          <el-input
            v-model="form.username"
            placeholder="用户名"
            :prefix-icon="User"
            class="!h-12"
          />
        </el-form-item>

        <el-form-item>
          <el-input
            v-model="form.email"
            placeholder="工作邮箱"
            :prefix-icon="Message"
            class="!h-12"
          />
        </el-form-item>

        <el-form-item>
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码 (至少8位)"
            :prefix-icon="Lock"
            show-password
            class="!h-12"
          />
        </el-form-item>

        <el-form-item>
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="确认密码"
            :prefix-icon="Lock"
            show-password
            class="!h-12"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            native-type="submit"
            :loading="loading"
            class="w-full !h-12 !text-lg !font-semibold !rounded-lg"
            round
          >
            立即注册
          </el-button>
        </el-form-item>

        <div class="text-center mt-4 text-sm">
          <span class="text-gray-500 mr-2 dark:text-gray-400">已有账号？</span>
          <router-link
            to="/login"
            class="text-medical-primary hover:underline font-medium"
            >返回登录</router-link
          >
        </div>
      </el-form>
    </div>
  </div>
</template>
