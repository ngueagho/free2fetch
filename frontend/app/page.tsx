import { Metadata } from 'next'
import { Hero } from '@/components/sections/hero'
import { Features } from '@/components/sections/features'
import { Pricing } from '@/components/sections/pricing'
import { Testimonials } from '@/components/sections/testimonials'
import { FAQ } from '@/components/sections/faq'
import { CTA } from '@/components/sections/cta'
import { Header } from '@/components/layout/header'
import { Footer } from '@/components/layout/footer'

export const metadata: Metadata = {
  title: 'Professional Course Downloader SaaS Platform',
  description: 'Download, stream, and manage your Udemy courses with our professional SaaS platform. Features include bulk downloads, video streaming, course sharing, and advanced analytics.',
  openGraph: {
    title: 'Free2Fetch - Professional Course Downloader',
    description: 'The most advanced course downloading platform for Udemy students and professionals.',
  },
}

export default function HomePage() {
  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <main className="flex-grow">
        <Hero />
        <Features />
        <Pricing />
        <Testimonials />
        <FAQ />
        <CTA />
      </main>
      <Footer />
    </div>
  )
}