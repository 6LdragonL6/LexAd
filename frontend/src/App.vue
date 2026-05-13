<script setup lang="ts">
// 根组件 —— 使用 DefaultLayout 包裹路由视图
import DefaultLayout from '@/layouts/DefaultLayout.vue'
</script>

<template>
  <DefaultLayout>
    <router-view />  <!-- 当前路由匹配的页面组件 -->
  </DefaultLayout>
</template>
