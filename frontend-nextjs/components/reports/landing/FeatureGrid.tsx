import type { LucideIcon } from "lucide-react"

export interface FeatureItem {
  icon: LucideIcon
  title: string
  description: string
}

interface FeatureGridProps {
  title: string
  subtitle: string
  features: FeatureItem[]
}

export function FeatureGrid({ title, subtitle, features }: FeatureGridProps) {
  return (
    <section className="py-20">
      <div className="mx-auto max-w-6xl px-4">
        <div className="mb-12 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            {title}
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
            {subtitle}
          </p>
        </div>

        {/* Exactly three features would leave an empty fourth cell on desktop —
            a visible hole where a card used to be. Only the 3 case is special-
            cased: 4, 6, 8 and 9 keep the four-column layout they were designed
            against. Tailwind needs whole class names, so this is a branch
            rather than an interpolated column count. */}
        <div className={`grid gap-6 sm:grid-cols-2 ${
          features.length === 3 ? 'lg:grid-cols-3' : 'lg:grid-cols-4'
        }`}>
          {features.map((feature) => {
            const Icon = feature.icon
            return (
              <div
                key={feature.title}
                className="group rounded-2xl bg-card p-6 ring-1 ring-border/50 transition-all hover:ring-primary/30 hover:shadow-lg"
              >
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary transition-colors group-hover:bg-primary/15">
                  <Icon className="h-6 w-6" />
                </div>
                <h3 className="mb-2 font-semibold text-foreground">{feature.title}</h3>
                <p className="text-sm leading-relaxed text-muted-foreground">{feature.description}</p>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
