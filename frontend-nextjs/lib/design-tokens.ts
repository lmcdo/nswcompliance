/**
 * Design Tokens - Complete Color System
 *
 * Authority Hierarchy: Purple (SEPP) > Blue (LEP) > Teal (DCP)
 * Semantic Colors: Muted professional palette for provisions
 */

// Authority-based tab colors (cool spectrum hierarchy)
export const AuthorityColors = {
    SEPP: {
        primary: '#9333ea',        // purple-600
        border: 'border-purple-500',
        bg: 'bg-purple-50',
        text: 'text-purple-700',
        hover: 'hover:bg-purple-100',
    },
    LEP: {
        primary: '#2563eb',        // blue-600
        border: 'border-blue-500',
        bg: 'bg-blue-50',
        text: 'text-blue-700',
        hover: 'hover:bg-blue-100',
    },
    DCP: {
        primary: '#14b8a6',        // teal-600
        border: 'border-teal-500',
        bg: 'bg-teal-50',
        text: 'text-teal-700',
        hover: 'hover:bg-teal-100',
    },
} as const;

// Semantic provision colors (muted professional palette)
// HSL-based for precise control of saturation/lightness
export const SemanticColors = {
    prohibited: {
        // Muted burgundy/rose - "not permitted" without alarm
        bg: 'bg-rose-50',           // hsl(355, 30%, 95%)
        border: 'border-rose-400',   // hsl(355, 35%, 55%)
        text: 'text-rose-800',       // hsl(355, 40%, 30%)
        icon: 'text-rose-600',
        hover: 'hover:bg-rose-100',
    },
    permitted: {
        // Muted sage/forest - "allowed" without celebration
        bg: 'bg-emerald-50',         // hsl(155, 28%, 95%)
        border: 'border-emerald-500', // hsl(155, 30%, 50%)
        text: 'text-emerald-900',    // hsl(155, 35%, 25%)
        icon: 'text-emerald-600',
        hover: 'hover:bg-emerald-100',
    },
    conditional: {
        // Muted gold/ochre - "review needed" without anxiety
        bg: 'bg-amber-50',           // hsl(45, 45%, 95%)
        border: 'border-amber-400',   // hsl(45, 50%, 55%)
        text: 'text-amber-900',       // hsl(45, 55%, 28%)
        icon: 'text-amber-600',
        hover: 'hover:bg-amber-100',
    },
    informational: {
        // Cool gray-blue - neutral context
        bg: 'bg-slate-50',
        border: 'border-slate-300',
        text: 'text-slate-700',
        icon: 'text-slate-500',
        hover: 'hover:bg-slate-100',
    },
} as const;

// Layer badges (semantic by provision layer type)
export const LayerBadges = {
    generic: {
        bg: 'bg-teal-500',
        text: 'text-white',
    },
    use_specific: {
        bg: 'bg-blue-500',
        text: 'text-white',
    },
    condition: {
        bg: 'bg-amber-500',
        text: 'text-white',
    },
    precinct: {
        bg: 'bg-purple-500',
        text: 'text-white',
    },
} as const;

// Status colors for property constraints
export const StatusColors = {
    Heritage: {
        bg: 'bg-amber-50',
        border: 'border-amber-300',
        icon: 'text-amber-600',
        text: 'text-amber-900',
    },
    TOD: {
        bg: 'bg-blue-50',
        border: 'border-blue-300',
        icon: 'text-blue-600',
        text: 'text-blue-900',
    },
    HIA: {
        bg: 'bg-emerald-50',
        border: 'border-emerald-300',
        icon: 'text-emerald-600',
        text: 'text-emerald-900',
    },
    Accelerated: {
        bg: 'bg-purple-50',
        border: 'border-purple-300',
        icon: 'text-purple-600',
        text: 'text-purple-900',
    },
} as const;

// Layout tokens
export const LayoutTokens = {
    card: {
        borderRadius: 'rounded-lg',
        borderLeftWidth: 'border-l-4',
        padding: 'p-4',
    },
    spacing: {
        sm: 'gap-2',
        md: 'gap-4',
        lg: 'gap-6',
    },
} as const;

// Helper function to get authority colors by context
export function getAuthorityColor(context: 'sepp' | 'lep' | 'dcp') {
    const map = {
        sepp: AuthorityColors.SEPP,
        lep: AuthorityColors.LEP,
        dcp: AuthorityColors.DCP,
    };
    return map[context];
}

// Helper function to get semantic colors by provision type
export function getSemanticColor(type: 'prohibited' | 'permitted' | 'conditional' | 'informational') {
    return SemanticColors[type];
}
