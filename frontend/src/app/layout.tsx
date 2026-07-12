import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";

export const metadata: Metadata = {
  title: "CareSyncAI : Contactless Telemedicine",
  description:
    "AI-powered gesture-controlled telemedicine platform. Reduce infection risk with contactless medical consultations.",
  keywords: ["telemedicine", "gesture control", "AI healthcare", "contactless medical"],
  openGraph: {
    title: "CareSync AI",
    description: "The future of contactless telemedicine",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="antialiased">
        <ErrorBoundary section="Application">
          <Providers>{children}</Providers>
        </ErrorBoundary>
      </body>
    </html>
  );
}
