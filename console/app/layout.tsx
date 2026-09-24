import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { THEME_BOOT } from "@/lib/theme";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
export const metadata: Metadata = {
  title: { default: "Troi", template: "%s · Troi" }, description: "Troi of Silo One: a chief of staff that lives on your Mac.",
  // on a phone the console installs to the Home Screen as an app: its own icon, no browser chrome, the status bar over our top bar
  manifest: "/manifest.webmanifest", appleWebApp: { capable: true, statusBarStyle: "black-translucent", title: "Troi" },
  icons: { icon: "/brand/favicon.svg", apple: "/brand/icon-512.png" }, formatDetection: { telephone: false },
};
export const viewport: Viewport = { width: "device-width", initialScale: 1, viewportFit: "cover", themeColor: "#02040a" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable} suppressHydrationWarning>
      <head><script dangerouslySetInnerHTML={{ __html: THEME_BOOT }} /></head>
      <body className="font-sans">{children}</body>
    </html>
  );
}
