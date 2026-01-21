// 獲取 CSS 變量的實際顏色值
export const getCSSVariable = (variableName) => {
  if (typeof window === 'undefined') return null
  try {
    const root = document.documentElement
    const value = getComputedStyle(root).getPropertyValue(variableName).trim()
    if (!value) return null
    // CSS 變量格式是 "12 76% 61%"，需要包裝成 "hsl(12 76% 61%)"
    if (value && !value.startsWith('hsl(') && !value.startsWith('#')) {
      return `hsl(${value})`
    }
    return value
  } catch (e) {
    console.error('Error getting CSS variable:', e)
    return null
  }
}

// 生成圖表顏色數組（支持至少35個顏色，確保不會撞色）
export const generateChartColors = (count = 35) => {
  // 獲取 CSS 變量中的基礎顏色
  const chart1 = getCSSVariable('--chart-1')
  const chart2 = getCSSVariable('--chart-2')
  const chart3 = getCSSVariable('--chart-3')
  const chart4 = getCSSVariable('--chart-4')
  const chart5 = getCSSVariable('--chart-5')
  
  // 基礎顏色數組（優先使用 CSS 變量，否則使用 fallback）
  const baseColors = [
    chart1 || 'hsl(12, 76%, 61%)',
    chart2 || 'hsl(173, 58%, 39%)',
    chart3 || 'hsl(197, 37%, 24%)',
    chart4 || 'hsl(43, 74%, 66%)',
    chart5 || 'hsl(27, 87%, 67%)',
    '#8b5cf6', // purple
    '#ec4899', // pink
    '#f59e0b', // amber
    '#10b981', // emerald
    '#3b82f6', // blue
    '#f97316', // orange
    '#14b8a6', // teal
    '#a855f7', // violet
    '#eab308', // yellow
    '#06b6d4', // cyan
  ]
  
  // 如果需要的顏色超過基礎顏色數，生成更多顏色
  const additionalColors = []
  
  // 使用HSL顏色空間均勻分布生成顏色
  for (let i = baseColors.length; i < count; i++) {
    // 在色相環上均勻分布（0-360度）
    // 使用黃金角度（137.508度）確保均勻分布
    const hue = (i * 137.508) % 360
    // 飽和度在60-80%之間變化
    const saturation = 60 + (i % 3) * 7
    // 亮度在45-65%之間變化
    const lightness = 45 + (i % 4) * 5
    additionalColors.push(`hsl(${hue}, ${saturation}%, ${lightness}%)`)
  }
  
  return [...baseColors, ...additionalColors]
}
