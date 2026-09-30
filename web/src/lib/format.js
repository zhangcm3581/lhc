export const pct = (x, d = 1) => (x == null ? '—' : (x * 100).toFixed(d) + '%')
export const fix = (x, d = 1) => (x == null ? '—' : x.toFixed(d))
export const signed = (x, d = 1) => (x == null ? '—' : (x > 0 ? '+' : '') + x.toFixed(d))
export const shortDate = (date) => date.slice(5)

// 本地记住上次的选择；隐私模式等情况下读写失败就用默认值
export function remember(key, fallback) {
  try {
    return localStorage.getItem('lhc:' + key) ?? fallback
  } catch {
    return fallback
  }
}
export function persist(key, value) {
  try {
    localStorage.setItem('lhc:' + key, value)
  } catch {}
}
