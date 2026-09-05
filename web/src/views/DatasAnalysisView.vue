<template>
  <div class="placeholder-page">
    <div class="placeholder-box">
      <a-result :title="t('comingSoon')" :sub-title="t('analysisPlanned')" />
    </div>
  </div>
</template>

<script setup>
import { t } from '@/i18n'
</script>

<style scoped>
.placeholder-page {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.placeholder-box {
  width: 100%;
  max-width: 480px;
}
</style>
