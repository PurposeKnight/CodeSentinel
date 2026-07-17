import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "CodeSentinel | Multi-Agent Code Reviewer",
  description: "Autonomous multi-agent code reviewer and vulnerability scanner dashboard.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <nav className="nav-container">
          <Link href="/" className="logo-link">
            <span className="pulsing-indicator"></span>
            <span className="logo-text">CODESENTINEL</span>
          </Link>
          <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--foreground-muted)', fontWeight: 500 }}>
              System Status: Active
            </span>
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
