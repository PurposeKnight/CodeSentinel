import { notFound } from "next/navigation";
import ReviewDetailClient from "@/components/ReviewDetailClient";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface AgentTask {
  id: string;
  review_id: string;
  agent: string;
  status: string;
  reason: string | null;
  report: any | null;
  created_at: string | null;
  updated_at: string | null;
}

interface PullRequestReview {
  id: string;
  repository: string;
  pull_request_number: number;
  delivery_id: string | null;
  status: string;
  score: number | null;
  security_score: number | null;
  performance_score: number | null;
  architecture_score: number | null;
  documentation_score: number | null;
  created_at: string;
  updated_at: string;
  tasks: AgentTask[];
}

async function getReview(id: string): Promise<PullRequestReview | null> {
  try {
    const res = await fetch(`${API_URL}/api/v1/reviews/${id}`, { cache: "no-store" });
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
  // Await the params if it's a Promise (in Next.js 15, dynamic route params are Promises)
  const resolvedParams = await params;
  const review = await getReview(resolvedParams.id);

  if (!review) {
    notFound();
  }

  return <ReviewDetailClient review={review} />;
}
