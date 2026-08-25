/**
 * 将可视化配置转为 6 位 cron 表达式（秒 分 时 日 月 周）
 */
export function buildCronExpression(config: {
  task_style: number
  second?: number
  minute?: number
  hour?: number
  day?: number
  month?: number
  week?: number
}) {
  const second = config.second ?? 0
  const minute = config.minute ?? 0
  const hour = config.hour ?? 0
  const day = config.day ?? 1
  const month = config.month ?? 1
  const week = config.week ?? 1

  switch (config.task_style) {
    case 1:
      return `0 ${minute} ${hour} * * *`
    case 2:
      return `0 ${minute} * * * *`
    case 3:
      return `0 ${minute} */${Math.max(hour, 1)} * * *`
    case 4:
      return `0 */${Math.max(minute, 1)} * * * *`
    case 5:
      return `*/${Math.max(second, 1)} * * * * *`
    case 6:
      return `0 ${minute} ${hour} * * ${week}`
    case 7:
      return `0 ${minute} ${hour} ${day} * *`
    case 8:
      return `0 ${minute} ${hour} ${day} ${month} *`
    default:
      return `0 ${minute} ${hour} * * *`
  }
}

/**
 * 从 cron 表达式反解析可视化配置（尽力匹配）
 */
export function parseCronExpression(expression?: string) {
  const defaults = {
    task_style: 1,
    second: 0,
    minute: 0,
    hour: 0,
    day: 1,
    month: 1,
    week: 1
  }
  if (!expression) return defaults

  const parts = expression.trim().split(/\s+/)
  if (parts.length < 6) return defaults

  const [secondPart, minutePart, hourPart, dayPart, monthPart, weekPart] = parts
  const extractNumber = (value: string, fallback = 0) => {
    if (value === '*') return fallback
    const stepMatch = value.match(/^\*\/(\d+)$/)
    if (stepMatch) return Number(stepMatch[1])
    const numMatch = value.match(/(\d+)/)
    return numMatch ? Number(numMatch[1]) : fallback
  }

  defaults.second = extractNumber(secondPart, 0)
  defaults.minute = extractNumber(minutePart, 0)
  defaults.hour = extractNumber(hourPart, 0)
  defaults.day = extractNumber(dayPart, 1)
  defaults.month = extractNumber(monthPart, 1)
  defaults.week = extractNumber(weekPart, 1)

  if (secondPart.startsWith('*/')) {
    defaults.task_style = 5
  } else if (minutePart.startsWith('*/')) {
    defaults.task_style = 4
  } else if (hourPart.startsWith('*/')) {
    defaults.task_style = 3
  } else if (weekPart !== '*') {
    defaults.task_style = 6
  } else if (dayPart !== '*' && monthPart !== '*') {
    defaults.task_style = 8
  } else if (dayPart !== '*') {
    defaults.task_style = 7
  } else if (hourPart === '*' && minutePart !== '*') {
    defaults.task_style = 2
  } else {
    defaults.task_style = 1
  }

  return defaults
}
