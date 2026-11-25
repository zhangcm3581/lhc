export function beijingToday() {
  return new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
}

export function issueForDate(date) {
  return Math.floor((Date.parse(`${date}T00:00:00Z`) - Date.UTC(Number(date.slice(0, 4)), 0, 1)) / 86400000) + 1
}

export function amountInCents(value, direction) {
  if (!/^(?:0|[1-9]\d{0,6})(?:\.\d{1,2})?$/.test(value)) throw new Error('请输入金额，最多两位小数')
  const [whole, fraction = ''] = value.split('.')
  const cents = Number(whole) * 100 + Number(fraction.padEnd(2, '0'))
  if (cents <= 0 || cents > 100000000) throw new Error('金额须大于 0 且不超过 1,000,000 元')
  return direction === 'win' ? cents : -cents
}

export function totals(records) {
  return records.reduce((sum, r) => {
    if (r.amount_cents > 0) sum.win += r.amount_cents
    else sum.loss -= r.amount_cents
    sum.net += r.amount_cents
    return sum
  }, { win: 0, loss: 0, net: 0 })
}
