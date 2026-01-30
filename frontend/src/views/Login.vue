<script setup>
import { ref, reactive } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import ThemeToggle from "../components/ThemeToggle.vue";
import { ElMessage } from "element-plus";
import { User, Lock, FirstAidKit } from "@element-plus/icons-vue";

const router = useRouter();
const authStore = useAuthStore();

const form = reactive({
  username: "",
  password: "",
});

const loading = ref(false);

const handleLogin = async () => {
  if (!form.username || !form.password) {
    ElMessage.warning("请输入用户名和密码");
    return;
  }

  loading.value = true;
  try {
    await authStore.login(form.username, form.password);
    ElMessage.success("登录成功");
    router.push("/");
  } catch (error) {
    if (error.detail) {
      ElMessage.error(`登录失败：${error.detail}`);
    } else {
      ElMessage.error("登录失败，请检查用户名或密码");
    }
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <div
    class="flex items-center justify-center min-h-screen bg-gradient-to-br from-gray-50 to-gray-200 dark:from-gray-900 dark:to-gray-800 relative"
  >
    <div class="absolute top-4 right-4 bg-white/80 backdrop-blur-sm p-2 rounded-full shadow-sm dark:bg-gray-800/80">
      <ThemeToggle />
    </div>
    <div
      class="w-full max-w-md p-10 bg-white rounded-xl shadow-lg border-t-4 border-medical-primary dark:bg-gray-800"
    >
      <div class="text-center mb-8">
        <el-icon class="text-medical-primary mb-2" :size="48">
          <FirstAidKit />
        </el-icon>
        <h2 class="text-2xl font-bold text-medical-primary mb-2">
          RamanAI 医疗平台
        </h2>
        <p class="text-sm text-gray-500 dark:text-gray-400">
          智能拉曼光谱辅助诊断系统
        </p>
      </div>

      <el-form :model="form" @submit.prevent="handleLogin" size="large">
        <el-form-item>
          <el-input
            v-model="form.username"
            placeholder="医生工号 / 用户名"
            :prefix-icon="User"
            class="!h-12"
          />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
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
            安全登录
          </el-button>
        </el-form-item>

        <div class="text-center mt-4 text-sm">
          <span class="text-gray-500 mr-2 dark:text-gray-400">新用户？</span>
          <router-link
            to="/register"
            class="text-medical-primary hover:underline font-medium"
            >注册账号</router-link
          >
        </div>
      </el-form>
    </div>
  </div>
</template>
