import './globals.css'

export const metadata = {
 title: 'NSW Development Compliance MVP',
 description: 'Inner West Council development compliance checker',
}

export default function RootLayout({
 children,
}: {
 children: React.ReactNode
}) {
 return (
 <html lang="en">
 <body>{children}</body>
 </html>
 )
}