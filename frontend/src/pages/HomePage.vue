<script setup lang="ts">
// 首页 —— 展示平台介绍和功能卡片，提供审查入口
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="home">
    <section class="hero">
      <h1>LexAd 广告合规审查</h1>
      <p class="hero-desc">
        覆盖法律、行业、平台三层审查体系，支持文本与图片广告合规检测。
      </p>
      <div class="hero-actions">
        <button class="btn btn-primary" @click="router.push('/review')">
          开始审查
        </button>
        <button class="btn btn-secondary" @click="router.push('/cases')">
          查看案例库
        </button>
      </div>
    </section>

    <section class="features">
      <div class="feature-card">
        <h3>三层审查</h3>
        <p>法律层面 &middot; 行业层面 &middot; 平台层面，逐层把关广告合规。</p>
      </div>
      <div class="feature-card">
        <h3>案例匹配</h3>
        <p>基于历史违规案例库，智能匹配相似场景与处罚参考。</p>
      </div>
      <div class="feature-card">
        <h3>改写建议</h3>
        <p>提供合规改写模板，帮助广告文案快速修正风险点。</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home { text-align: center; }

.hero {
  padding: 3rem 0 2rem;
}

.hero h1 {
  font-size: 2.2rem;
  color: #1a1a2e;
  margin-bottom: 0.75rem;
}

.hero-desc {
  font-size: 1.05rem;
  color: #555;
  max-width: 520px;
  margin: 0 auto 2rem;
}

.hero-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
}

.btn {
  padding: 0.6rem 1.8rem;
  border-radius: 6px;
  font-size: 0.95rem;
  border: none;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-primary {
  background: #e94560;
  color: #fff;
}

.btn-secondary {
  background: #eee;
  color: #333;
}

.btn:hover { opacity: 0.85; }

.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1.5rem;
  margin-top: 2.5rem;
}

.feature-card {
  background: #f8f8f8;
  padding: 1.5rem;
  border-radius: 8px;
  text-align: left;
}

.feature-card h3 {
  margin: 0 0 0.5rem;
  color: #1a1a2e;
}

.feature-card p {
  color: #666;
  font-size: 0.9rem;
  line-height: 1.5;
}
</style>
