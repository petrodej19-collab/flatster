import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts"

interface PriceEntry {
  price: string
  date: string
}

export function PriceHistoryChart({ history }: { history: PriceEntry[] }) {
  if (history.length === 0) return null

  const data = history.map((entry) => ({
    date: entry.date,
    price: Number(entry.price),
  }))

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <XAxis dataKey="date" tick={{ fontSize: 12 }} />
          <YAxis
            tick={{ fontSize: 12 }}
            tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
          />
          <Tooltip
            formatter={(value) =>
              new Intl.NumberFormat("sl-SI", {
                style: "currency",
                currency: "EUR",
              }).format(Number(value))
            }
          />
          <Line
            type="monotone"
            dataKey="price"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
            dot={data.length === 1}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
