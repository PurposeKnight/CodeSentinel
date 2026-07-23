import { notFound, redirect } from "next/navigation";
import { cookies } from "next/headers";
import ReviewDetailClient, { PullRequestReview } from "@/components/ReviewDetailClient";

const API_URL = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function getReview(id: string, token: string): Promise<PullRequestReview | null> {
  try {
    const res = await fetch(`${API_URL}/api/v1/reviews/${id}`, {
      headers: { Cookie: `session_token=${token}` },
      cache: "no-store",
    });
    if (res.status === 404) {
      return null;
    }
    if (!res.ok) {
      throw new Error(`Failed to fetch review details (status ${res.status})`);
    }
    return await res.json();
  } catch (error) {
    console.error("Error fetching review details:", error);
    return null;
  }
}

export default async function ReviewDetailPage({
  params,
}: {
  params: Promise<{ id: string }> | { id: string };
}) {
  const cookieStore = await cookies();
  const sessionToken = cookieStore.get("session_token")?.value;
  if (!sessionToken) {
    redirect("/login");
  }

  // Await the params if it's a Promise (in Next.js 15, dynamic route params are Promises)
  const resolvedParams = await params;
  const review = await getReview(resolvedParams.id, sessionToken);

  if (!review) {
    notFound();
  }

  return <ReviewDetailClient review={review} />;
}
