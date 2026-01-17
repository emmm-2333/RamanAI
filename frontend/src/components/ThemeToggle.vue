<script setup>
import { useDark, useToggle } from '@vueuse/core'
import { Sunny, Moon } from '@element-plus/icons-vue'

// 使用 VueUse 的 useDark 自动管理 class="dark"
const isDark = useDark()
const toggleDark = useToggle(isDark)
</script>

<template>
  <el-switch
    v-model="isDark"
    inline-prompt
    :active-icon="Moon"
    :inactive-icon="Sunny"
    style="--el-switch-on-color: #2c2c2c; --el-switch-off-color: #f2f2f2"
    @change="toggleDark"
  />
</template>

<style scoped>
/* 可以在这里微调样式 */
</style>
