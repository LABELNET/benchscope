<template>
  <div class="accuracy-page">
    <div class="planned-card">
      <a-result
        status="info"
        :title="t('planned')"
        :sub-title="t('plannedDesc')"
      >
        <template #extra>
          <a-tag color="blue" style="font-size: 14px; padding: 4px 16px">{{ t('expectedVersion') }}</a-tag>
        </template>
      </a-result>
      <div class="features">
        <a-row :gutter="24" justify="center">
          <a-col :xs="24" :sm="8" v-for="feat in features" :key="feat.title">
            <a-card size="small" class="feature-card" hoverable>
              <template #cover>
                <div class="feature-icon">{{ feat.icon }}</div>
              </template>
              <a-card-meta :title="feat.title" :description="feat.desc" />
            </a-card>
          </a-col>
        </a-row>
      </div>
    </div>
  </div>
</template>

<script setup>
import { t } from '@/i18n'

const features = [
  { icon: '📊', title: '数据集精度评估', desc: '在常见数据集上评估模型精度与质量' },
  { icon: '🔗', title: 'ModelScope 模型对比', desc: '官方模型链接与对比结论分析' },
  { icon: '📈', title: '多维度质量分析', desc: '从多个维度分析和比较模型表现' },
]
</script>

<style scoped>
.accuracy-page {
  height: 100%;
  overflow: auto;
  padding: 40px 20px;
  display: flex;
  justify-content: center;
}
.planned-card {
  max-width: 900px;
  width: 100%;
}
.features {
  margin-top: 24px;
}
.feature-card {
  text-align: center;
  border-radius: 8px;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.feature-card :deep(.ant-card-body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.feature-card :deep(.ant-card-meta-title) {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 14px;
}
.feature-card :deep(.ant-card-meta-description) {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 40px;
  line-height: 20px;
  margin-top: 4px;
  font-size: 12px;
}
.feature-icon {
  font-size: 48px;
  padding-top: 24px;
}
</style>
