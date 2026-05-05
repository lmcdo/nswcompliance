import type { StatItem, Testimonial } from "./types"

interface SocialProofProps {
  stats: StatItem[]
  testimonials: Testimonial[]
}

export function SocialProof({ stats, testimonials }: SocialProofProps) {
  return (
    <section className="py-16">
      <div className="mx-auto max-w-6xl px-4">
        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-16">
          {stats.map((stat) => (
            <div key={stat.label} className="text-center">
              <p className="text-2xl md:text-3xl font-bold text-foreground">{stat.value}</p>
              <p className="text-xs md:text-sm text-muted-foreground mt-1">{stat.label}</p>
            </div>
          ))}
        </div>

        {/* Testimonials */}
        <div className="grid md:grid-cols-3 gap-4">
          {testimonials.map((testimonial, i) => (
            <div
              key={i}
              className="bg-card border border-border/50 rounded-xl p-5 hover:border-border transition-colors"
            >
              <p className="text-sm text-foreground leading-relaxed mb-4">
                &quot;{testimonial.quote}&quot;
              </p>
              <div className="flex items-center gap-3">
                <div className="size-8 rounded-full bg-muted flex items-center justify-center text-xs font-medium text-muted-foreground">
                  {testimonial.author.split(" ").map(n => n[0]).join("")}
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground">{testimonial.author}</p>
                  <p className="text-xs text-muted-foreground">{testimonial.role}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
