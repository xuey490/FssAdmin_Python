<template>
  <div class="taixu-platform" v-loading="loadingStats">
    <ElRow class="platform-header art-card mb-5 max-sm:mb-4">
      <ElCol :span="9" class="user-panel">
        <ElAvatar :size="50" :src="userInfo.avatar || undefined">
          <i class="ri-user-line"></i>
        </ElAvatar>
        <div class="user-meta">
          <div>
            <span>{{ userInfo.username || userInfo.nickname || 'admin' }}</span>
            <span class="meta-gap">系统管理员</span>
          </div>
          <div class="sub-line">
            <span>{{ userInfo.phone || '15555555555' }}</span>
            <span class="meta-gap">{{ userInfo.email || 'xuex126@126.com' }}</span>
          </div>
        </div>
      </ElCol>

      <ElCol :span="6" class="weather-panel" v-loading="loadingWeather">
        <div class="weather-line">
          <span>{{ weather?.cityInfo?.city || '西安市' }}</span>
          <span>{{ todayWeather?.type || '多云' }}</span>
          <span>{{ todayWeather?.low || '低温 24℃' }}</span>
          <span>{{ todayWeather?.high || '高温 32℃' }}</span>
          <span>{{ todayWeather?.fx || '东风' }}</span>
        </div>
        <div class="sub-line">{{ todayWeather?.notice || '晴雨之间，请防紫外线侵扰' }}</div>
      </ElCol>

      <ElCol :span="9" class="stat-panel">
        <ElStatistic
          title="用户数"
          :value="userCount"
          :value-style="{ color: '#2bfa14', fontSize: '18px' }"
        >
          <template #prefix>
            <i class="ri-account-circle-line stat-user-icon"></i>
          </template>
        </ElStatistic>
        <ElStatistic
          title="访问量"
          :value="visitCount"
          :value-style="{ color: '#faad14', fontSize: '18px' }"
        >
          <template #prefix>
            <i class="ri-global-line stat-visit-icon"></i>
          </template>
        </ElStatistic>
        <ElTooltip content="刷新数据">
          <i class="ri-loop-right-line refresh-icon" @click="refreshAll"></i>
        </ElTooltip>
      </ElCol>
    </ElRow>

    <ElRow :gutter="20" class="pie-row mb-5 max-sm:mb-4">
      <ElCol :span="8">
        <section class="art-card chart-card">
          <div class="chart-card-header"><i class="ri-apps-line"></i>模型统计</div>
          <div ref="modelChartRef" class="pie-chart"></div>
        </section>
      </ElCol>
      <ElCol :span="8">
        <section class="art-card chart-card">
          <div class="chart-card-header"><i class="ri-pie-chart-line"></i>RAG检索</div>
          <div ref="ragChartRef" class="pie-chart"></div>
        </section>
      </ElCol>
      <ElCol :span="8">
        <section class="art-card chart-card">
          <div class="chart-card-header"><i class="ri-donut-chart-line"></i>Agent智能</div>
          <div ref="agentChartRef" class="pie-chart"></div>
        </section>
      </ElCol>
    </ElRow>

    <ElRow :gutter="20" class="trend-row">
      <ElCol :span="12">
        <section class="art-card chart-card">
          <div class="chart-card-header"><i class="ri-bar-chart-2-line"></i>RAG检索</div>
          <div ref="ragTrendChartRef" class="trend-chart"></div>
        </section>
      </ElCol>
      <ElCol :span="12">
        <section class="art-card chart-card">
          <div class="chart-card-header"><i class="ri-bar-chart-box-line"></i>Agent智能</div>
          <div ref="agentTrendChartRef" class="trend-chart"></div>
        </section>
      </ElCol>
    </ElRow>
  </div>
</template>

<script setup lang="ts">
  import { computed, nextTick, onMounted, ref } from 'vue'
  import { ElMessage } from 'element-plus'
  import { fetchTaixuHomeStats, fetchTaixuHomeWeather } from '@/api/taixu'
  import { useChart } from '@/hooks/core/useChart'
  import type { EChartsOption } from '@/plugins/echarts'
  import { useUserStore } from '@/store/modules/user'

  defineOptions({ name: 'TaixuPlatformPage' })

  type WeatherForecast = {
    type?: string
    low?: string
    high?: string
    fx?: string
    notice?: string
  }

  type WeatherData = {
    cityInfo?: { city?: string }
    data?: { forecast?: WeatherForecast[] }
  }

  type HomeStats = {
    user_count?: number
    visit_count?: number
    model_dicts?: Record<string, number>
    history_records?: Record<string, string[]>
    memory_details?: Record<string, { number?: number; time?: number }>
  }

  type DialogStats = {
    ragDialogNumbers: Record<string, number>
    ragResponseTimes: Record<string, number>
    agentDialogNumbers: Record<string, number>
    agentResponseTimes: Record<string, number>
  }

  const cityCode = '101010100'
  const userStore = useUserStore()
  const userInfo = computed(() => userStore.getUserInfo)
  const loadingWeather = ref(false)
  const loadingStats = ref(false)
  const weather = ref<WeatherData | null>(null)
  const stats = ref<HomeStats | null>(null)
  const userCount = ref(0)
  const visitCount = ref(0)

  const todayWeather = computed(() => weather.value?.data?.forecast?.[0])

  const {
    chartRef: modelChartRef,
    initChart: initModelChart,
    updateChart: updateModelChart,
    handleResize: resizeModelChart
  } = useChart()
  const {
    chartRef: ragChartRef,
    initChart: initRagChart,
    updateChart: updateRagChart,
    handleResize: resizeRagChart
  } = useChart()
  const {
    chartRef: agentChartRef,
    initChart: initAgentChart,
    updateChart: updateAgentChart,
    handleResize: resizeAgentChart
  } = useChart()
  const {
    chartRef: ragTrendChartRef,
    initChart: initRagTrendChart,
    updateChart: updateRagTrendChart,
    handleResize: resizeRagTrendChart
  } = useChart()
  const {
    chartRef: agentTrendChartRef,
    initChart: initAgentTrendChart,
    updateChart: updateAgentTrendChart,
    handleResize: resizeAgentTrendChart
  } = useChart()

  const modelTypes = [
    { value: 'llm', label: 'LLM' },
    { value: 'embedding', label: 'Embedding' },
    { value: 'medical', label: 'Medical' },
    { value: 'vision', label: 'Vision' }
  ]

  const ragPatterns = [
    'NativeRAG',
    'MultiQuery',
    'RAGFusion',
    'SubQuestion',
    'StepBack',
    'HYDE',
    'RoutingLogic',
    'RoutingSemantic',
    'QueryConstruction',
    'MultiRepresentation',
    'RAPTOR'
  ]
  const ragAdvances = ['Corrective', 'SelfCheck', 'Adaptive']
  const ragSpecials = ['Graph', 'KeyWord', 'Hybrid', 'KMean', 'MMR']
  const ragApply = ['support', 'arxiv', 'program']
  const agentPatterns = [
    'ReAct',
    'ReWOO',
    'PlanExecute',
    'LLMCompile',
    'Reflection',
    'SelfDiscover',
    'Reflexion',
    'LATS'
  ]
  const agentAdvances = ['Supervisor', 'Collaboration', 'Hierarchical']
  const agentApply = ['search', 'topic', 'sentiment', 'travel']

  const pieTitle = (text: string, subtext: string): EChartsOption['title'] => ({
    text,
    subtext,
    left: 'center'
  })

  const pieOption = (
    title: string,
    subtext: string,
    legendData: string[],
    data: Array<{ value: number; name: string }>,
    seriesName = '检索统计'
  ): EChartsOption => ({
    title: pieTitle(title, subtext),
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b} : {c} ({d}%)'
    },
    grid: {
      left: 50,
      right: 40,
      bottom: 30
    },
    legend: {
      orient: 'vertical',
      right: 0,
      top: 0,
      data: legendData,
      padding: 20
    },
    toolbox: { show: false },
    series: [
      {
        name: seriesName,
        type: 'pie',
        radius: '60%',
        center: ['50%', '63%'],
        data
      }
    ]
  })

  const trendOption = (
    title: string,
    dialogNumbers: Record<string, number>,
    responseTimes: Record<string, number>,
    axisInterval: number
  ): EChartsOption => ({
    title: {
      text: title,
      subtext: '',
      left: 'center'
    },
    tooltip: { trigger: 'axis' },
    toolbox: { show: false },
    legend: {
      orient: 'horizontal',
      right: 0,
      top: 0,
      data: ['历史对话数量', '平均响应时间'],
      padding: 20
    },
    xAxis: [
      {
        type: 'category',
        data: Object.keys(dialogNumbers),
        axisLabel: { interval: axisInterval }
      }
    ],
    yAxis: [
      {
        type: 'value',
        name: '历史对话数量',
        axisLabel: { formatter: '{value}' }
      },
      {
        type: 'value',
        name: '平均响应时间',
        axisLabel: { formatter: '{value} s' }
      }
    ],
    grid: {
      left: 50,
      right: 60,
      top: 80,
      bottom: 50,
      containLabel: true
    },
    series: [
      {
        name: '历史对话数量',
        type: 'bar',
        data: Object.values(dialogNumbers)
      },
      {
        name: '平均响应时间',
        type: 'line',
        yAxisIndex: 1,
        data: Object.values(responseTimes)
      }
    ]
  })

  const buildMemoryDialog = (
    keys: string[],
    source: string,
    numbers: Record<string, number>,
    times: Record<string, number>,
    dialogNumbers: Record<string, number>,
    responseTimes: Record<string, number>
  ) => {
    keys.forEach((itemKey) => {
      const key = `${source}-${itemKey}`
      dialogNumbers[itemKey] = numbers[key] || 0
      responseTimes[itemKey] = times[key] || 0
    })
  }

  const buildMemoryProgram = (
    keys: string[],
    numbers: Record<string, number>,
    times: Record<string, number>,
    dialogNumbers: Record<string, number>,
    responseTimes: Record<string, number>
  ) => {
    keys.forEach((itemKey) => {
      const matchedKeys = Object.keys(numbers).filter((key) => key.includes(itemKey))
      const totalNumber = matchedKeys.reduce((sum, key) => sum + (numbers[key] || 0), 0)
      const totalTime = matchedKeys.reduce((sum, key) => sum + (times[key] || 0), 0)
      dialogNumbers[itemKey] = totalNumber
      responseTimes[itemKey] = matchedKeys.length ? Math.trunc(totalTime / matchedKeys.length) : 0
    })
  }

  const processHistoryMemory = (
    historyRecords: NonNullable<HomeStats['history_records']>,
    memoryDetails: NonNullable<HomeStats['memory_details']>
  ): DialogStats => {
    const numbers: Record<string, number> = {}
    const times: Record<string, number> = {}

    Object.keys(historyRecords).forEach((historyKey) => {
      let number = 0
      let time = 0
      historyRecords[historyKey].forEach((sourceId) => {
        const detail = memoryDetails[sourceId]
        number += Number(detail?.number || 0)
        time += Number(detail?.time || 0)
      })
      numbers[historyKey] = number
      times[historyKey] = number ? Math.trunc(time / number) : 0
    })

    const ragDialogNumbers: Record<string, number> = {}
    const ragResponseTimes: Record<string, number> = {}
    buildMemoryDialog(ragPatterns, 'retrieval', numbers, times, ragDialogNumbers, ragResponseTimes)
    buildMemoryDialog(ragAdvances, 'advance', numbers, times, ragDialogNumbers, ragResponseTimes)
    buildMemoryDialog(ragSpecials, 'special', numbers, times, ragDialogNumbers, ragResponseTimes)
    buildMemoryProgram(ragApply, numbers, times, ragDialogNumbers, ragResponseTimes)

    const agentDialogNumbers: Record<string, number> = {}
    const agentResponseTimes: Record<string, number> = {}
    buildMemoryDialog(
      agentPatterns,
      'answer',
      numbers,
      times,
      agentDialogNumbers,
      agentResponseTimes
    )
    buildMemoryDialog(
      agentAdvances,
      'agentic',
      numbers,
      times,
      agentDialogNumbers,
      agentResponseTimes
    )
    buildMemoryProgram(agentApply, numbers, times, agentDialogNumbers, agentResponseTimes)

    return { ragDialogNumbers, ragResponseTimes, agentDialogNumbers, agentResponseTimes }
  }

  const renderCharts = async () => {
    const data = stats.value || {}
    const modelDicts = data.model_dicts || {}
    const historyRecords = data.history_records || {}
    const memoryDetails = data.memory_details || {}
    const dialogStats = processHistoryMemory(historyRecords, memoryDetails)

    const modelOption = pieOption(
      '模型统计',
      '模型数量统计',
      modelTypes.map((item) => item.label),
      modelTypes.map((item) => ({ value: modelDicts[item.value] || 0, name: item.label }))
    )
    const ragOption = pieOption(
      'RAG检索',
      'RAG模式与应用数量统计',
      ['文档检索', '智能检索', '特殊检索', 'RAG应用'],
      [
        { value: ragPatterns.length, name: '文档检索' },
        { value: ragAdvances.length, name: '智能检索' },
        { value: ragSpecials.length, name: '特殊检索' },
        { value: ragApply.length, name: 'RAG应用' }
      ]
    )
    const agentOption = pieOption(
      'Agent智能',
      'Agent模式与应用数量统计',
      ['智能模式', '多智能体', 'Agent应用'],
      [
        { value: agentPatterns.length, name: '智能模式' },
        { value: agentAdvances.length, name: '多智能体' },
        { value: agentApply.length, name: 'Agent应用' }
      ],
      '智能统计'
    )
    const ragTrendOption = trendOption(
      'RAG：历史对话数量与平均响应时间',
      dialogStats.ragDialogNumbers,
      dialogStats.ragResponseTimes,
      2
    )
    const agentTrendOption = trendOption(
      'Agent：历史对话数量与平均响应时间',
      dialogStats.agentDialogNumbers,
      dialogStats.agentResponseTimes,
      1
    )

    await nextTick()
    initModelChart(modelOption)
    initRagChart(ragOption)
    initAgentChart(agentOption)
    initRagTrendChart(ragTrendOption)
    initAgentTrendChart(agentTrendOption)
    updateModelChart(modelOption)
    updateRagChart(ragOption)
    updateAgentChart(agentOption)
    updateRagTrendChart(ragTrendOption)
    updateAgentTrendChart(agentTrendOption)
    await nextTick()
    resizeModelChart()
    resizeRagChart()
    resizeAgentChart()
    resizeRagTrendChart()
    resizeAgentTrendChart()
  }

  const loadWeather = async () => {
    loadingWeather.value = true
    try {
      weather.value = await fetchTaixuHomeWeather(cityCode)
    } catch (e: any) {
      ElMessage.error(e?.message || '获取天气失败')
    } finally {
      loadingWeather.value = false
    }
  }

  const loadStats = async () => {
    loadingStats.value = true
    try {
      stats.value = await fetchTaixuHomeStats()
      userCount.value = Number(stats.value?.user_count || 0)
      visitCount.value = Number(stats.value?.visit_count || 0)
      await renderCharts()
    } catch (e: any) {
      ElMessage.error(e?.message || '获取统计失败')
    } finally {
      loadingStats.value = false
    }
  }

  const refreshAll = () => {
    void loadWeather()
    void loadStats()
  }

  onMounted(() => {
    refreshAll()
  })
</script>

<style scoped lang="scss">
  .taixu-platform {
    display: flex;
    flex-direction: column;
    padding-bottom: 20px;
    color: var(--el-text-color-primary);
  }

  .platform-header {
    flex-shrink: 0;
    height: 80px;
    padding: 15px 0;
  }

  .user-panel {
    display: flex;
    align-items: center;
    padding-left: 8%;
  }

  .user-meta {
    padding-left: 20px;
    line-height: 1.6;
  }

  .meta-gap {
    padding-left: 20px;
  }

  .sub-line {
    color: var(--el-text-color-regular);
  }

  .weather-panel {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
  }

  .weather-line {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 0 10px;
    padding-bottom: 7px;
  }

  .stat-panel {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 40px;
  }

  .stat-user-icon {
    margin-right: 10px;
    color: #2bfa14;
  }

  .stat-visit-icon {
    margin-right: 10px;
    color: #faad14;
  }

  .refresh-icon {
    position: absolute;
    top: 2px;
    right: 26px;
    font-size: 20px;
    color: #b1b0b0;
    cursor: pointer;
  }

  .pie-row .chart-card {
    min-height: 360px;
  }

  .trend-row .chart-card {
    min-height: 420px;
  }

  .chart-card {
    display: flex;
    flex-direction: column;
  }

  .chart-card-header {
    height: 40px;
    padding-left: 15px;
    line-height: 40px;
    border-bottom: 1px solid var(--el-border-color-light);
    background: var(--default-box-color);

    i {
      padding-right: 10px;
    }
  }

  .pie-chart,
  .trend-chart {
    width: 100%;
  }

  .pie-chart {
    height: 320px;
  }

  .trend-chart {
    height: 380px;
  }
</style>
