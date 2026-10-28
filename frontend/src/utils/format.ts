export const formatNumber = (value: number) => new Intl.NumberFormat('en-US').format(value)
export const formatBytes = (value: number) => `${(value / 1024 / 1024).toFixed(1)} MB`
