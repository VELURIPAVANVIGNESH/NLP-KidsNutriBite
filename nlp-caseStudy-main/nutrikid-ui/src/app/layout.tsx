import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'NutriKid — Pediatric Nutrition RAG System',
  description:
    'Evidence-grounded pediatric nutrition RAG system. Retrieval-augmented intelligence for children aged 5–15 using WHO, ICMR-NIN, FAO, and FSSAI institutional sources.',
  keywords: [
    'pediatric nutrition',
    'RAG system',
    'NutriKid',
    'evidence-grounded AI',
    'ICMR-NIN',
    'WHO nutrition guidelines',
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
          rel="stylesheet"
        />
      </head>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
