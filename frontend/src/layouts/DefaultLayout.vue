<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
const navItems = [
  { path: '/', label: '首页' },
  { path: '/review', label: '广告审查' },
  { path: '/cases', label: '案例库' },
  { path: '/templates', label: '模板库' },
]
</script>

<template>
  <div class="app-shell">
    <header class="navbar">
      <div class="navbar-brand">
        <router-link to="/" class="brand-link">LexAd</router-link>
        <span class="brand-subtitle">广告合规审查平台</span>
      </div>
      <nav class="navbar-links">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-link"
          active-class="nav-link--active"
        >
          {{ item.label }}
        </router-link>
      </nav>
    </header>
    <main class="main-content">
      <slot />
    </main>
    <footer class="footer">
      <p>LexAd v0.2.0 &mdash; Demo 占位结果，不构成真实合规意见。</p>
    </footer>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2rem;
  height: 56px;
  background: #1a1a2e;
  color: #eee;
}

.brand-link {
  font-size: 1.25rem;
  font-weight: 700;
  color: #e94560;
  text-decoration: none;
}

.brand-subtitle {
  margin-left: 0.75rem;
  font-size: 0.8rem;
  color: #999;
}

.navbar-links {
  display: flex;
  gap: 1.5rem;
}

.nav-link {
  color: #ccc;
  text-decoration: none;
  font-size: 0.9rem;
  padding: 0.25rem 0;
  border-bottom: 2px solid transparent;
  transition: color 0.2s, border-color 0.2s;
}

.nav-link:hover {
  color: #fff;
}

.nav-link--active {
  color: #e94560;
  border-bottom-color: #e94560;
}

.main-content {
  flex: 1;
  max-width: 1100px;
  width: 100%;
  margin: 0 auto;
  padding: 2rem 1.5rem;
}

.footer {
  text-align: center;
  padding: 1rem;
  font-size: 0.8rem;
  color: #888;
  border-top: 1px solid #eee;
}
</style>
