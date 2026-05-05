interface TrustSource {
  name: string
  logo: string
}

interface TrustBarProps {
  sources: TrustSource[]
}

export function TrustBar({ sources }: TrustBarProps) {
  return (
    <section className="py-8 border-y border-border/50">
      <div className="flex flex-col md:flex-row items-center justify-center gap-4 md:gap-8">
        <p className="text-xs text-muted-foreground uppercase tracking-wider font-medium">
          Data sourced from
        </p>
        <div className="flex items-center gap-6 md:gap-8">
          {sources.map((source) => (
            <div
              key={source.name}
              className="flex items-center gap-2 text-muted-foreground/70 hover:text-muted-foreground transition-colors"
            >
              <div className="size-6 rounded bg-muted flex items-center justify-center text-[10px] font-bold">
                {source.logo}
              </div>
              <span className="text-xs font-medium hidden sm:inline">{source.name}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
