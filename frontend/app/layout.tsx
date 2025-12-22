import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Providers } from '@/components/providers'
import { Toaster } from '@/components/ui/toaster'
import { cn } from '@/lib/utils'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })

export const metadata: Metadata = {
  title: {
    default: 'Free2Fetch - Professional Course Downloader',
    template: '%s | Free2Fetch'
  },
  description: 'Professional SaaS platform for downloading and managing Udemy courses with advanced features including streaming, sharing, and analytics.',
  keywords: [
    'udemy downloader',
    'course downloader',
    'video downloader',
    'e-learning',
    'education technology',
    'saas platform',
    'course management',
    'video streaming'
  ],
  authors: [{ name: 'Free2Fetch Team' }],
  creator: 'Free2Fetch',
  publisher: 'Free2Fetch',
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: process.env.NEXT_PUBLIC_APP_URL,
    title: 'Free2Fetch - Professional Course Downloader',
    description: 'Professional SaaS platform for downloading and managing Udemy courses with advanced features.',
    siteName: 'Free2Fetch',
    images: [
      {
        url: '/images/og-image.png',
        width: 1200,
        height: 630,
        alt: 'Free2Fetch - Professional Course Downloader',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Free2Fetch - Professional Course Downloader',
    description: 'Professional SaaS platform for downloading and managing Udemy courses.',
    images: ['/images/twitter-image.png'],
    creator: '@free2fetch',
  },
  icons: {
    icon: [
      { url: '/favicon.ico' },
      { url: '/icons/icon-16x16.png', sizes: '16x16', type: 'image/png' },
      { url: '/icons/icon-32x32.png', sizes: '32x32', type: 'image/png' },
    ],
    shortcut: '/favicon.ico',
    apple: '/icons/apple-touch-icon.png',
  },
  manifest: '/manifest.json',
  alternates: {
    canonical: process.env.NEXT_PUBLIC_APP_URL,
  },
  verification: {
    google: 'google-verification-code',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="theme-color" content="#000000" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
      </head>
      <body
        className={cn(
          'min-h-screen bg-background font-sans antialiased',
          inter.variable
        )}
      >
        <Providers>
          {children}
          <Toaster />
        </Providers>
      </body>
    </html>
  )
}