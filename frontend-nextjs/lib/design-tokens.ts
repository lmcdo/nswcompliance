export const AuthorityColors = {
    LEP: {
        primary: '#2563eb', // blue-600
        border: 'border-blue-500',
        bg: 'bg-blue-50',
        text: 'text-blue-700',
        hover: 'hover:bg-blue-100',
    },
    DCP: {
        primary: '#059669', // emerald-600
        border: 'border-green-500',
        bg: 'bg-green-50',
        text: 'text-green-700',
        hover: 'hover:bg-green-100',
    },
    SEPP: {
        primary: '#9333ea', // purple-600
        border: 'border-purple-500',
        bg: 'bg-purple-50',
        text: 'text-purple-700',
        hover: 'hover:bg-purple-100',
    },
} as const;

export const LayerBadges = {
    generic: {
        bg: 'bg-teal-500',  // #14b8a6 - matches legend and border
        text: 'text-white',
    },
    use_specific: {
        bg: 'bg-blue-500',  // #3b82f6 - matches legend and border
        text: 'text-white',
    },
    condition: {
        bg: 'bg-amber-500',  // #f59e0b - matches legend and border
        text: 'text-white',
    },
    precinct: {
        bg: 'bg-purple-500',  // #8b5cf6 - matches legend and border
        text: 'text-white',
    },
} as const;

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
        bg: 'bg-green-50',
        border: 'border-green-300',
        icon: 'text-green-600',
        text: 'text-green-900',
    },
    Accelerated: {
        bg: 'bg-purple-50',
        border: 'border-purple-300',
        icon: 'text-purple-600',
        text: 'text-purple-900',
    },
} as const;

export const LayoutTokens = {
    card: {
        borderRadius: 'rounded-lg', // 0.5rem
        borderLeftWidth: 'border-l-4',
        padding: 'p-4',
    },
    spacing: {
        sm: 'gap-2',
        md: 'gap-4',
        lg: 'gap-6',
    },
} as const;
