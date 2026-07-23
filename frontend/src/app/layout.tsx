import type { Metadata } from "next";
import "./globals.css";
import { cookies } from "next/headers";
import NavProfile from "@/components/NavProfile";
import NavLinks from "@/components/NavLinks";

const API_URL = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const metadata: Metadata = {
  title: "CodeSentinel | Multi-Agent Code Reviewer",
  description: "Autonomous multi-agent code reviewer and vulnerability scanner dashboard.",
};

interface User {
  id: string;
  github_id: number;
  username: string;
  email: string | null;
  avatar_url: string | null;
  created_at: string | null;
}

async function getMe(): Promise<User | null> {
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
          <NavLinks showRepos={!!user} />
          <NavProfile user={user} />
        </nav>
        {children}
      </body>
    </html>
  );
}
