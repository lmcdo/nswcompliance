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
        // Provision theme colors for dynamic theming (purple/green/amber)
        'bg-purple-100', 'text-purple-700', 'before:text-purple-500',
        'bg-green-100', 'text-green-700', 'before:text-green-500',
        'bg-amber-100', 'text-amber-700', 'before:text-amber-500',
        // Card colors for tab theming
        'bg-purple-50', 'bg-purple-200', 'text-purple-600', 'text-purple-800', 'text-purple-900',
        'border-purple-100', 'border-purple-200', 'border-purple-300', 'hover:bg-purple-50', 'hover:bg-purple-100',
        'bg-green-50', 'bg-green-200', 'text-green-600', 'text-green-800', 'text-green-900',
        'border-green-100', 'border-green-200', 'hover:bg-green-100', 'hover:text-green-800',
        'bg-amber-50', 'bg-amber-200', 'text-amber-600', 'text-amber-800', 'text-amber-900',
        'border-amber-200', 'border-amber-300', 'border-amber-500', 'hover:text-amber-700', 'hover:text-amber-800',
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