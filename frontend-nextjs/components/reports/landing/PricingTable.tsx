import { Check, Minus } from "lucide-react"
import type { ComparisonRow } from "./types"

interface PricingTableProps {
  title: string
  subtitle: string
  price: string
  comparison: ComparisonRow[]
  methodology: string
}

export function PricingTable({ title, subtitle, price, comparison, methodology }: PricingTableProps) {
  return (
    <section className="bg-card/30 py-20">
      <div className="mx-auto max-w-4xl px-4">
        {/* Section header */}
        <div className="mb-12 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            {title}
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-lg text-muted-foreground">
            {subtitle}
          </p>
        </div>

        {/* Comparison table */}
        <div className="overflow-hidden rounded-2xl bg-card ring-1 ring-border/50">
          {/* Header */}
          <div className="grid grid-cols-3 border-b border-border/50 bg-muted/30">
            <div className="p-4 font-semibold text-foreground">Feature</div>
            <div className="p-4 text-center font-semibold text-foreground">Free</div>
            <div className="relative p-4 text-center font-semibold text-foreground">
              <span className="rounded-full bg-primary px-3 py-1 text-sm text-primary-foreground">{price}</span>
            </div>
          </div>

          {/* Rows */}
          {comparison.map((row, index) => (
            <div
              key={row.name}
              className={`grid grid-cols-3 ${index !== comparison.length - 1 ? "border-b border-border/30" : ""}`}
            >
              <div className="p-4 text-sm text-foreground">{row.name}</div>
              <div className="flex items-center justify-center p-4">
                {row.free ? (
                  <Check className="h-5 w-5 text-accent" />
                ) : (
                  <Minus className="h-5 w-5 text-muted-foreground/40" />
                )}
              </div>
              <div className="flex items-center justify-center p-4">
                <Check className="h-5 w-5 text-accent" />
              </div>
            </div>
          ))}
        </div>

        {/* How it works */}
        <div className="mt-12 rounded-2xl bg-muted/50 p-6 sm:p-8">
          <h3 className="mb-4 text-lg font-semibold text-foreground">How It Works</h3>
          <p className="text-sm leading-relaxed text-muted-foreground">
            {methodology}
          </p>
        </div>
      </div>
    </section>
  )
}
