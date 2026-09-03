import type { Metadata } from "next";
import { Space_Grotesk, Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  weight: ["500", "600", "700"],
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  weight: ["400", "500", "600"],
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  weight: ["500", "700"],
});

export const metadata: Metadata = {
  title: "BidVerify AI — GeM Integrated Bid Compliance Verification Platform",
  description: "AI-Powered Integrated Bid Compliance Verification Platform for GeM Procurement",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`h-full ${spaceGrotesk.variable} ${inter.variable} ${jetbrainsMono.variable}`}>
      <body className={`${inter.className} min-h-full flex flex-col bg-[#F5F8F7] text-slate-900 antialiased selection:bg-emerald-500 selection:text-white`}>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
