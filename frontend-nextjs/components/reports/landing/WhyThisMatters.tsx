import type { ComparisonCard, WhatYouGetItem } from "./types"

interface WhyThisMattersProps {
  comparisons: ComparisonCard[]
  whatYouGet: WhatYouGetItem[]
}

export function WhyThisMatters({ comparisons, whatYouGet }: WhyThisMattersProps) {
  return (
    <section id="how-it-works" className="py-16">
      <div className="text-center mb-12">
        <h2 className="text-2xl font-bold text-foreground mb-3">
          Why existing checks fall short
        </h2>
        <p className="text-muted-foreground max-w-lg mx-auto">
          Standard information tells you if there might be a problem.
          We tell you exactly how bad it is.
        </p>
      </div>

      {/* Problem/solution comparison */}
      <div className="grid md:grid-cols-3 gap-4 mb-16">
        {comparisons.map((item, i) => (
          <div key={i} className="bg-card border border-border/50 rounded-xl p-5">
            <p className="text-xs text-muted-foreground uppercase tracking-wider mb-2">
              {item.problem}
            </p>
            <p className="text-sm text-foreground/70 mb-3 line-through decoration-destructive/50">
              {item.limitation}
            </p>
            <p className="text-sm text-foreground font-medium flex items-center gap-2">
              <svg className="size-4 text-accent flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
              {item.solution}
            </p>
          </div>
        ))}
      </div>

      {/* What you get */}
      {whatYouGet.length > 0 && (
        <div className="bg-muted/30 rounded-2xl p-6 md:p-8">
          <h3 className="text-lg font-semibold text-foreground mb-6">What you get in your report</h3>
          <div className="grid md:grid-cols-3 gap-6">
            {whatYouGet.map((item) => (
              <div key={item.title} className="flex gap-4">
                <div className="size-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center flex-shrink-0">
                  <svg className="size-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <p className="font-medium text-foreground mb-1">{item.title}</p>
                  <p className="text-sm text-muted-foreground">{item.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
