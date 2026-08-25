/**
 * 内置模型下载目录（Models 页宫格数据）。
 * intro 为双语（zh/en），展示时按当前界面语言取用。
 */
export const modelCatalog = [
  {
    id: 'deepseek-v3',
    name: 'DeepSeek-V3',
    org: 'DeepSeek AI',
    color: '#4D6BFE',
    short: 'DS',
    intro: {
      zh: 'DeepSeek 开源 MoE 大语言模型，671B 总参数量（37B 激活），长上下文与推理能力出色，广泛用于性能基准测试。',
      en: 'DeepSeek open-source MoE LLM with 671B total params (37B active), strong long-context and reasoning, widely used for performance benchmarking.',
    },
    precision: ['BF16', 'FP8', 'W8A8'],
    homepage: 'https://huggingface.co/deepseek-ai/DeepSeek-V3',
    download: 'huggingface-cli download deepseek-ai/DeepSeek-V3 --local-dir ./DeepSeek-V3',
  },
  {
    id: 'deepseek-r1',
    name: 'DeepSeek-R1',
    org: 'DeepSeek AI',
    color: '#2E5BFF',
    short: 'R1',
    intro: {
      zh: 'DeepSeek 开源推理增强模型，671B MoE，擅长数学、代码与复杂推理任务。',
      en: 'DeepSeek reasoning-enhanced open model, 671B MoE, excels at math, code and complex reasoning.',
    },
    precision: ['BF16', 'FP8', 'W8A8'],
    homepage: 'https://huggingface.co/deepseek-ai/DeepSeek-R1',
    download: 'huggingface-cli download deepseek-ai/DeepSeek-R1 --local-dir ./DeepSeek-R1',
  },
  {
    id: 'qwen2.5-72b',
    name: 'Qwen2.5-72B-Instruct',
    org: 'Alibaba Qwen',
    color: '#7B3FE4',
    short: 'QW',
    intro: {
      zh: '阿里通义千问 2.5 系列最大指令模型，72B 稠密参数，中英文能力均衡，支持 AWQ/GPTQ 量化。',
      en: 'Alibaba Qwen2.5 flagship instruct model, 72B dense params, balanced bilingual ability, supports AWQ/GPTQ quantization.',
    },
    precision: ['BF16', 'FP8', 'AWQ', 'GPTQ'],
    homepage: 'https://huggingface.co/Qwen/Qwen2.5-72B-Instruct',
    download: 'huggingface-cli download Qwen/Qwen2.5-72B-Instruct --local-dir ./Qwen2.5-72B-Instruct',
  },
  {
    id: 'llama-3.1-70b',
    name: 'Llama-3.1-70B-Instruct',
    org: 'Meta AI',
    color: '#0866FF',
    short: 'Ll',
    intro: {
      zh: 'Meta Llama 3.1 系列 70B 指令模型，128K 上下文，社区生态与工具链完善。',
      en: 'Meta Llama 3.1 70B instruct model, 128K context, mature ecosystem and tooling.',
    },
    precision: ['BF16', 'FP8', 'AWQ'],
    homepage: 'https://huggingface.co/meta-llama/Llama-3.1-70B-Instruct',
    download: 'huggingface-cli download meta-llama/Llama-3.1-70B-Instruct --local-dir ./Llama-3.1-70B-Instruct',
  },
  {
    id: 'glm-4-9b',
    name: 'GLM-4-9B',
    org: 'Zhipu AI',
    color: '#2BB673',
    short: 'GL',
    intro: {
      zh: '智谱 AI 开源双语对话模型，9B 参数，支持 128K 上下文，可本地部署。',
      en: 'Zhipu AI open bilingual chat model, 9B params, 128K context, deployable locally.',
    },
    precision: ['BF16', 'FP16', 'INT4'],
    homepage: 'https://huggingface.co/THUDM/glm-4-9b',
    download: 'huggingface-cli download THUDM/glm-4-9b --local-dir ./glm-4-9b',
  },
  {
    id: 'internlm2.5-7b',
    name: 'InternLM2.5-7B',
    org: 'Shanghai AI Lab',
    color: '#E85D3F',
    short: 'IL',
    intro: {
      zh: '上海人工智能实验室书生·浦语 2.5 对话模型，7B 参数，工具调用与数学推理能力强。',
      en: 'Shanghai AI Lab InternLM2.5 chat model, 7B params, strong tool calling and math reasoning.',
    },
    precision: ['BF16', 'FP16'],
    homepage: 'https://huggingface.co/internlm/internlm2_5-7b',
    download: 'huggingface-cli download internlm/internlm2_5-7b --local-dir ./internlm2_5-7b',
  },
]
