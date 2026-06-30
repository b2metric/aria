import type { Metadata } from "next";
import localFont from "next/font/local";
// @b2m-team/ui shadcn HSL tokens — imported BEFORE globals.css so the app's own
// brand tokens win on the few shared names (--success/--warning/--info).
import "@b2m-team/ui/styles.css";
import "./globals.css";
import { AuthProvider } from "@/components/AuthProvider";
import { Sidebar } from "@/components/Sidebar";
import { THEME_INIT_SCRIPT } from "@/lib/theme-script";

// B2Metric brand typeface (licensed). Exposes --font-apercu; globals.css
// uses it ahead of the system fallback stack.
const apercu = localFont({
  src: [
    { path: "./fonts/Apercu_Regular.otf", weight: "400", style: "normal" },
    { path: "./fonts/Apercu_Medium.otf", weight: "500", style: "normal" },
    { path: "./fonts/Apercu_Bold.otf", weight: "700", style: "normal" },
  ],
  variable: "--font-apercu",
  display: "swap",
});

export const metadata: Metadata = {
  title: "ARIA — AI-Driven Analytics",
  description: "Conversational BI platform. Ask questions, get charts.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`h-full ${apercu.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="h-full bg-gray-50 antialiased">
        <AuthProvider>
          <div className="flex h-full flex-col md:flex-row overflow-hidden">
            <Sidebar />
            <main className="flex-1 min-w-0 overflow-auto relative">{children}</main>
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
