import Link from "next/link";
import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

const API_URL = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
}

async function getReviews(token: string): Promise<PullRequestReview[]> {
  try {
    const res = await fetch(`${API_URL}/api/v1/reviews`, {
      headers: { Cookie: `session_token=${token}` },
      cache: "no-store",
    });
    if (!res.ok) {
      throw new Error("Failed to fetch reviews");
    }
    return await res.json();
  } catch (error) {
    console.error("Error fetching reviews:", error);
    return [];
  }
}

export default async function DashboardPage() {
  const cookieStore = await cookies();
  const sessionToken = cookieStore.get("session_token")?.value;
  if (!sessionToken) {
    redirect("/login");
  }

  const reviews = await getReviews(sessionToken);

  // Compute metrics
  const totalReviews = reviews.length;
  const completedReviews = reviews.filter((r) => r.status === "completed").length;
  const runningReviews = reviews.filter((r) => r.status === "running").length;
  
  // Calculate average score of completed reviews
  const completedWithScore = reviews.filter((r) => r.status === "completed" && r.score !== null);
  const avgScore = completedWithScore.length > 0
    ? Math.round(completedWithScore.reduce((sum, r) => sum + (r.score || 0), 0) / completedWithScore.length)
    : null;

  return (
    <main className="main-wrapper">
      <header style={{ marginBottom: "40px" }}>
        <h1 style={{ fontSize: "2rem", marginBottom: "8px", fontWeight: 700 }}>
          Code Review Dashboard
        </h1>
        <p style={{ color: "var(--foreground-muted)" }}>
          Monitor security reviews, code quality scores, and analysis tasks.
        </p>
      </header>

      {/* Summary Cards Grid */}
      <section className="summary-grid">
        <div className="glass-card summary-card">
          <div className="summary-card-label">Total PR Reviews</div>
          <div className="summary-card-value">{totalReviews}</div>
        </div>
        <div className="glass-card summary-card">
          <div className="summary-card-label">Average Quality Score</div>
          <div className="summary-card-value" style={{ color: avgScore && avgScore >= 80 ? "var(--accent-success)" : avgScore ? "var(--accent-warning)" : "var(--foreground-muted)" }}>
            {avgScore !== null ? `${avgScore}%` : "N/A"}
          </div>
        </div>
        <div className="glass-card summary-card">
          <div className="summary-card-label">Completed Runs</div>
          <div className="summary-card-value">{completedReviews}</div>
        </div>
        <div className="glass-card summary-card">
          <div className="summary-card-label">Active Scans</div>
          <div className="summary-card-value" style={{ color: "var(--accent-warning)" }}>
            {runningReviews}
          </div>
        </div>
      </section>

      {/* Reviews Table */}
      <section className="glass-card" style={{ padding: "8px" }}>
        <div className="table-wrapper">
          {reviews.length === 0 ? (
            <div style={{ padding: "40px", textAlign: "center", color: "var(--foreground-muted)" }}>
              <p style={{ marginBottom: "16px" }}>No reviews found in database.</p>
              <p style={{ fontSize: "0.85rem" }}>
                Make a POST request or trigger a pull request webhook on the backend to initialize scans.
              </p>
            </div>
          ) : (
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Repository</th>
                  <th>Pull Request</th>
                  <th>Status</th>
                  <th>Quality Index</th>
                  <th>Trigger Date</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {reviews.map((review) => {
                  const score = review.score;
                  const isScoreNull = score === null;
                  const scoreClass = isScoreNull 
                    ? "" 
                    : score >= 80 
                      ? "score-high" 
                      : score >= 50 
                        ? "score-mid" 
                        : "score-low";

                  return (
                    <tr key={review.id}>
                      <td style={{ fontWeight: 600 }}>{review.repository}</td>
                      <td>PR #{review.pull_request_number}</td>
                      <td>
                        <span className={`badge-status badge-status-${review.status}`}>
                          {review.status}
                        </span>
                      </td>
                      <td>
                        {isScoreNull ? (
                          <span style={{ color: "var(--foreground-muted)" }}>N/A</span>
                        ) : (
                          <div className={`score-badge-circle ${scoreClass}`}>
                            {score}%
                          </div>
                        )}
                      </td>
                      <td style={{ color: "var(--foreground-muted)", fontSize: "0.875rem" }}>
                        {new Date(review.created_at).toLocaleDateString(undefined, {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </td>
                      <td>
                        <Link href={`/reviews/${review.id}`} className="action-button">
                          View Details
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </main>
  );
}
