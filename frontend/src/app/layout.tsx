import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";
import { cookies } from "next/headers";
import NavProfile from "@/components/NavProfile";

const API_URL = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const metadata: Metadata = {
  title: "CodeSentinel | Multi-Agent Code Reviewer",
  description: "Autonomous multi-agent code reviewer and vulnerability scanner dashboard.",
};

async function getMe(): Promise<any | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get("session_token")?.value;
  if (!token) return null;

  try {
    const res = await fetch(`${API_URL}/api/v1/auth/me`, {
      headers: { Cookie: `session_token=${token}` },
      cache: "no-store",
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (e) {
    console.error("Error fetching current user profile:", e);
  }
  return null;
}

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const user = await getMe();

  return (
    <html lang="en">
      <body>
        <nav className="nav-container">
          <div style={{ display: "flex", alignItems: "center", gap: "32px" }}>
            <Link href="/" className="logo-link" style={{ marginRight: "8px" }}>
              <span className="pulsing-indicator"></span>
              <span className="logo-text">CODESENTINEL</span>
            </Link>
            {user && (
              <Link 
                href="/repositories" 
                style={{ 
                  textDecoration: "none", 
                  fontSize: "0.875rem", 
                  fontWeight: 600, 
                  color: "var(--foreground-muted)",
                  transition: "color 0.2s ease" 
                }}
                onMouseEnter={(e) => e.currentTarget.style.color = "var(--foreground)"}
                onMouseLeave={(e) => e.currentTarget.style.color = "var(--foreground-muted)"}
              >
                Repositories
              </Link>
            )}
          </div>
          <NavProfile user={user} />
        </nav>
        {children}
      </body>
    </html>
  );
}
