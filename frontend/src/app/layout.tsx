import type { Metadata, Viewport } from "next";
import { Inter, Sora } from "next/font/google";
import { AuthProvider } from "@/lib/auth";
import "./globals.css";

const sans = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const display = Sora({ subsets: ["latin"], variable: "--font-display", display: "swap" });

export const metadata: Metadata = {
  title: "AI Video Cloner — Reconstruction vidéo par IA",
  description:
    "Analysez vos vidéos, extrayez les personnages, reconstruisez chaque scène et obtenez des prompts détaillés pour Veo, Google Flow, Kling et Runway.",
};
export const viewport: Viewport = { themeColor: "#06070f", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className={`${sans.variable} ${display.variable}`}>
      <body className="min-h-screen font-sans">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
