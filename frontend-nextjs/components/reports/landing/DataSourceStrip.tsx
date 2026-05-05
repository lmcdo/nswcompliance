import { Shield } from "lucide-react"
import type { LucideIcon } from "lucide-react"

export interface DataSourceItem {
  icon: LucideIcon
  name: string
  description: string
}

interface DataSourceStripProps {
  sources: DataSourceItem[]
}

export function DataSourceStrip({ sources }: DataSourceStripProps) {
  return (
    <section className="border-y border-border/50 bg-card/50 py-10">
      <div className="mx-auto max-w-6xl px-4">
        <div className="mb-8 flex items-center justify-center gap-2 text-center">
          <Shield className="h-4 w-4 text-accent" />
          <span className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
            Verified Data Sources
          </span>
        </div>

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7">
          {sources.map((source) => {
            const Icon = source.icon
            return (
              <div
                key={source.name}
                className="group flex flex-col items-center rounded-xl bg-background/80 p-4 text-center ring-1 ring-border/50 transition-all hover:ring-primary/30 hover:shadow-md"
              >
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary transition-colors group-hover:bg-primary/15">
                  <Icon className="h-5 w-5" />
                </div>
                <div className="text-xs font-semibold text-foreground">{source.name}</div>
                <div className="mt-0.5 text-[11px] text-muted-foreground">{source.description}</div>
              </div>
            )
          })}
        </div>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          All sources are independent — a positive from one confirms or contradicts another
        </p>
      </div>
    </section>
  )
}
