import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/components/AuthProvider";
import { Sidebar } from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "ARIA — AI-Driven Analytics",
  description: "Conversational BI platform. Ask questions, get charts.",
};

// Applies the saved (or system) theme before paint to avoid a flash of the
// wrong theme on load. Runs synchronously in <head> ahead of hydration.
const themeScript = `(function(){try{var t=localStorage.getItem('theme');if(!t){t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}document.documentElement.setAttribute('data-theme',t);}catch(e){}})();`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
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
