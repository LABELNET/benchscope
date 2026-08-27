<template>
  <div class="placeholder-page">
    <a-empty :description="t('evalsPlanned')" />
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
</style>
