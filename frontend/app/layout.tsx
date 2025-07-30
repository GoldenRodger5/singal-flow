import './globals.css'
import { Inter } from 'next/font/google'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'Signal Flow - AI Trading Dashboard',
  description: 'Real-time AI-powered trading system monitoring',
  icons: {
    icon: '/favicon.svg',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen bg-gray-900 text-white">
          {children}
        </div>
      </body>
    </html>
  )
}
