/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: ["class"],
    content: [
        './pages/**/*.{ts,tsx}',
        './components/**/*.{ts,tsx}',
        './app/**/*.{ts,tsx}',
        './src/**/*.{ts,tsx}',
    ],
    safelist: [
        // Authority Colors - SEPP (Purple)
        'bg-purple-50', 'bg-purple-100', 'bg-purple-200', 'bg-purple-600', 'bg-purple-700',
        'text-purple-100', 'text-purple-400', 'text-purple-600', 'text-purple-700', 'text-purple-800', 'text-purple-900',
        'border-purple-100', 'border-purple-200', 'border-purple-300', 'border-purple-500',
        'hover:bg-purple-50', 'hover:bg-purple-100', 'hover:bg-purple-100/50', 'hover:text-purple-800',

        // Authority Colors - LEP (Blue)
        'bg-blue-50', 'bg-blue-100', 'bg-blue-200', 'bg-blue-600', 'bg-blue-700',
        'text-blue-100', 'text-blue-400', 'text-blue-600', 'text-blue-700', 'text-blue-800', 'text-blue-900',
        'border-blue-100', 'border-blue-200', 'border-blue-300', 'border-blue-500',
        'hover:bg-blue-50', 'hover:bg-blue-100', 'hover:bg-blue-100/50', 'hover:text-blue-800',

        // Authority Colors - DCP (Teal)
        'bg-teal-50', 'bg-teal-100', 'bg-teal-200', 'bg-teal-600', 'bg-teal-700',
        'text-teal-100', 'text-teal-400', 'text-teal-600', 'text-teal-700', 'text-teal-800', 'text-teal-900',
        'border-teal-100', 'border-teal-200', 'border-teal-300', 'border-teal-500',
        'hover:bg-teal-50', 'hover:bg-teal-100', 'hover:bg-teal-100/50', 'hover:text-teal-800',

        // Semantic Colors - Prohibited (Rose/Burgundy)
        'bg-rose-50', 'bg-rose-100', 'text-rose-600', 'text-rose-800', 'text-rose-900',
        'border-rose-400', 'hover:bg-rose-100',

        // Semantic Colors - Permitted (Emerald/Sage)
        'bg-emerald-50', 'bg-emerald-100', 'text-emerald-600', 'text-emerald-900',
        'border-emerald-500', 'hover:bg-emerald-100',

        // Semantic Colors - Conditional (Amber/Gold)
        'bg-amber-50', 'bg-amber-100', 'text-amber-600', 'text-amber-900',
        'border-amber-400', 'hover:bg-amber-100',

        // Semantic Colors - Informational (Slate)
        'bg-slate-50', 'bg-slate-100', 'text-slate-500', 'text-slate-700',
        'border-slate-300', 'hover:bg-slate-100',

        // Layer Badges
        'bg-teal-500', 'bg-blue-500', 'bg-amber-500', 'bg-purple-500',

        // Universal
        'text-white', 'ring-2',

        // Provision text formatter theme colors
        'before:text-purple-500', 'before:text-blue-500', 'before:text-teal-500',
    ],
    theme: {
        container: {
            center: true,
            padding: "2rem",
            screens: {
                "2xl": "1400px",
            },
        },
        extend: {
            colors: {
                border: "hsl(var(--border))",
                input: "hsl(var(--input))",
                ring: "hsl(var(--ring))",
                background: "hsl(var(--background))",
                foreground: "hsl(var(--foreground))",
                primary: {
                    DEFAULT: "hsl(var(--primary))",
                    foreground: "hsl(var(--primary-foreground))",
                },
                secondary: {
                    DEFAULT: "hsl(var(--secondary))",
                    foreground: "hsl(var(--secondary-foreground))",
                },
                destructive: {
                    DEFAULT: "hsl(var(--destructive))",
                    foreground: "hsl(var(--destructive-foreground))",
                },
                muted: {
                    DEFAULT: "hsl(var(--muted))",
                    foreground: "hsl(var(--muted-foreground))",
                },
                accent: {
                    DEFAULT: "hsl(var(--accent))",
                    foreground: "hsl(var(--accent-foreground))",
                },
                popover: {
                    DEFAULT: "hsl(var(--popover))",
                    foreground: "hsl(var(--popover-foreground))",
                },
                card: {
                    DEFAULT: "hsl(var(--card))",
                    foreground: "hsl(var(--card-foreground))",
                },
            },
            borderRadius: {
                lg: "var(--radius)",
                md: "calc(var(--radius) - 2px)",
                sm: "calc(var(--radius) - 4px)",
            },
            keyframes: {
                "accordion-down": {
                    from: { height: 0 },
                    to: { height: "var(--radix-accordion-content-height)" },
                },
                "accordion-up": {
                    from: { height: "var(--radix-accordion-content-height)" },
                    to: { height: 0 },
                },
                "slide-in": {
                    from: { opacity: 0, transform: "translateY(20px)" },
                    to: { opacity: 1, transform: "translateY(0)" },
                },
            },
            animation: {
                "accordion-down": "accordion-down 0.2s ease-out",
                "accordion-up": "accordion-up 0.2s ease-out",
                "slide-in": "slide-in 0.3s ease-out",
            },
        },
    },
    plugins: [require("tailwindcss-animate")],
}