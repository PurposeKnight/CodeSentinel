import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import RepositoriesListClient from "@/components/RepositoriesListClient";

const API_URL = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Repository {
  id: number;
  name: string;
  full_name: string;
  html_url: string;
  description: string | null;
  is_linked: boolean;
}

async function getRepositories(token: string): Promise<Repository[]> {
  try {
    const res = await fetch(`${API_URL}/api/v1/repositories`, {
      headers: { Cookie: `session_token=${token}` },
      cache: "no-store",
    });
    if (!res.ok) {
      throw new Error(`Failed to fetch repositories (status ${res.status})`);
    }
    return await res.json();
  } catch (error) {
    console.error("Error fetching repositories list:", error);
    return [];
  }
}

export default async function RepositoriesPage() {
  const cookieStore = await cookies();
  const sessionToken = cookieStore.get("session_token")?.value;
  if (!sessionToken) {
    redirect("/login");
  }

  const repositories = await getRepositories(sessionToken);

  return <RepositoriesListClient initialRepos={repositories} />;
}
