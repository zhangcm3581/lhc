// 生肖、号码、波色等固定规则

export const ZODIACS = [...'鼠牛虎兔龙蛇马羊猴鸡狗猪']
export const zIndex = (z) => ZODIACS.indexOf(z)
const mod12 = (x) => ((x % 12) + 12) % 12

// 本命生肖 = 01、13、25、37、49 对应的生肖，春节当天切换。任一号码都能反推。
export const benmingOf = (nums, zodiacs) => ZODIACS[mod12(zIndex(zodiacs[0]) + nums[0] - 1)]

// 本命年为 benming 时，生肖 z 对应的号码（本命 5 个，其余 4 个）
export function numbersOf(z, benming) {
  const out = []
  for (let n = mod12(zIndex(benming) - zIndex(z)) + 1; n <= 49; n += 12) out.push(n)
  return out
}

const RED = new Set([1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46])
const BLUE = new Set([3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48])
export const colorOf = (n) => (RED.has(n) ? 'red' : BLUE.has(n) ? 'blue' : 'green')
export const pad = (n) => String(n).padStart(2, '0')

// 号码范围：特码只看第 7 个号；平码 7 个号都算（特码的生肖买平码也算中）
export const SCOPES = {
  特码: (d) => [d.zodiacs[6]],
  平码: (d) => [...new Set(d.zodiacs)],
}

function comb(n, r) {
  let c = 1
  for (let i = 0; i < r; i++) c = (c * (n - i)) / (i + 1)
  return c
}
// 一期里某生肖（对应 k 个号码）出现的理论概率
export const PROB = {
  特码: (k) => k / 49,
  平码: (k) => 1 - comb(49 - k, 7) / comb(49, 7),
}
