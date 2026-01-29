<script setup>
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import ThemeToggle from '../components/ThemeToggle.vue';
import {
  FirstAidKit,
  User,
  SwitchButton,
  Monitor,
  DataLine,
  Setting,
  Cpu
} from '@element-plus/icons-vue';

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const handleLogout = () => {
  authStore.logout();
  router.push('/login');
};
</script>

<template>
  <el-container class="h-screen flex flex-col bg-medical-bg dark:bg-gray-900 transition-colors duration-300">
    <!-- Header -->
    <el-header class="!h-16 flex justify-between items-center px-6 bg-medical-primary text-white shadow-md z-10 dark:bg-gray-800 dark:border-b dark:border-gray-700">
      <div class="flex items-center gap-3 cursor-pointer" @click="router.push('/')">
        <el-icon class="text-white" :size="28"><FirstAidKit /></el-icon>
        <span class="text-xl font-semibold tracking-wide">RamanAI 医疗平台</span>
      </div>
      <div class="flex items-center gap-6">
        <div class="flex items-center gap-3 bg-white/10 px-4 py-1.5 rounded-full backdrop-blur-sm" v-if="authStore.user">
          <el-avatar :size="32" :icon="User" class="bg-white/20 text-white" />
          <span class="text-sm font-medium">{{ authStore.user.username }}</span>
          <span class="text-xs bg-white/20 px-2 py-0.5 rounded-full">{{ authStore.user.role }}</span>
        </div>
        <div class="flex items-center gap-3">
          <ThemeToggle />
          <el-popconfirm title="确定要退出登录吗？" confirm-button-text="退出" cancel-button-text="取消" confirm-button-type="danger" @confirm="handleLogout">
            <template #reference>
              <el-button type="danger" circle plain class="!border-none !bg-white/10 hover:!bg-white/20 !text-white">
                <el-icon><SwitchButton /></el-icon>
              </el-button>
            </template>
          </el-popconfirm>
        </div>
      </div>
    </el-header>

    <el-container class="flex-1 overflow-hidden">
      <!-- Sidebar Menu -->
      <el-aside width="240px" class="bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700">
        <el-menu
          :default-active="route.path"
          class="!border-r-0 h-full"
          router
          :background-color="isDark ? '#1f2937' : '#ffffff'"
          :text-color="isDark ? '#e5e7eb' : '#374151'"
          :active-text-color="'#0072C6'"
        >
          <el-menu-item index="/dashboard">
            <el-icon><Monitor /></el-icon>
            <span>诊断工作台</span>
          </el-menu-item>
          
          <el-menu-item index="/records">
            <el-icon><DataLine /></el-icon>
            <span>光谱记录管理</span>
          </el-menu-item>
          
          <el-menu-item index="/models">
            <el-icon><Cpu /></el-icon>
            <span>模型版本管理</span>
          </el-menu-item>
          
          <el-menu-item index="/analysis">
            <el-icon><Setting /></el-icon>
            <span>高级数据分析</span>
          </el-menu-item>
          
          <!-- <el-menu-item index="/device">
            <el-icon><Setting /></el-icon>
            <span>设备采集</span>
          </el-menu-item> -->
        </el-menu>
      </el-aside>

      <!-- Main Content -->
      <el-main class="!p-0 bg-gray-50 dark:bg-gray-900 overflow-hidden flex flex-col">
        <router-view v-slot="{ Component }">
          <transition name="el-fade-in-linear" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.el-menu-item.is-active {
  background-color: rgba(0, 114, 198, 0.1) !important;
  border-right: 3px solid #0072C6;
}
</style>
