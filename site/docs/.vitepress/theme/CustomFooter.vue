<script setup lang="ts">
</script>

<template>
  <footer class="custom-footer">
    <div class="custom-footer-container">
      <div class="footer-left">
        <div class="footer-name">OpenMLR</div>
        <div class="footer-copyright">Copyright © 2025 Anubhav Singh. Released under the MIT License.</div>
      </div>
      <div class="footer-right">
        <a href="/sitemap.xml" target="_blank" rel="noopener">Sitemap</a>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.custom-footer {
  border-top: 1px solid var(--vp-c-divider);
  padding: 24px 24px;
  background-color: var(--vp-c-bg);
}

.custom-footer-container {
  max-width: 1152px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.footer-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.footer-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--vp-c-text-1);
}

.footer-copyright {
  font-size: 13px;
  color: var(--vp-c-text-2);
}

.footer-right {
  display: flex;
  gap: 16px;
}

.footer-right a {
  font-size: 13px;
  color: var(--vp-c-text-2);
  text-decoration: none;
  transition: color 0.2s;
}

.footer-right a:hover {
  color: var(--vp-c-brand-1);
}

@media (max-width: 640px) {
  .custom-footer-container {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
