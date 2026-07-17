"use client";

import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Repository {
  id: number;
  name: string;
  full_name: string;
  html_url: string;
  description: string | null;
  is_linked: boolean;
}

export default function RepositoriesListClient({ initialRepos }: { initialRepos: Repository[] }) {
  const [repos, setRepos] = useState<Repository[]>(initialRepos);
  const [loadingRepoId, setLoadingRepoId] = useState<number | null>(null);

  const handleToggleLink = async (repo: Repository) => {
    setLoadingRepoId(repo.id);
    const action = repo.is_linked ? "unlink" : "link";
    try {
      const res = await fetch(`${API_URL}/api/v1/repositories/${action}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ repository: repo.full_name }),
        credentials: "include",
      });

      if (res.ok) {
        setRepos((prevRepos) =>
          prevRepos.map((r) =>
            r.id === repo.id ? { ...r, is_linked: !repo.is_linked } : r
          )
        );
      } else {
        const errData = await res.json();
        alert(`Error: ${errData.detail || "Failed to update repository link status"}`);
      }
    } catch (e) {
      console.error(`Error toggling link for ${repo.full_name}:`, e);
      alert("Network error: failed to communicate with CodeSentinel API");
    } finally {
      setLoadingRepoId(null);
    }
  };

  return (
    <main className="main-wrapper">
      <header style={{ marginBottom: "40px" }}>
        <h1 style={{ fontSize: "2rem", marginBottom: "8px", fontWeight: 700 }}>
          Repository Integrations
        </h1>
        <p style={{ color: "var(--foreground-muted)" }}>
          Enable or disable autonomous security reviews and quality audits for your GitHub repositories.
        </p>
      </header>

      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))", gap: "24px" }}>
        {repos.length === 0 ? (
          <div style={{ gridColumn: "1/-1", padding: "80px 40px", textAlign: "center", color: "var(--foreground-muted)" }} className="glass-card">
            <p style={{ marginBottom: "12px", fontSize: "1.1rem" }}>No repositories discovered on your GitHub profile.</p>
            <p style={{ fontSize: "0.85rem" }}>Check organization permissions or configure custom token access levels.</p>
          </div>
        ) : (
          repos.map((repo) => (
            <div key={repo.id} className="glass-card" style={{ padding: "28px", display: "flex", flexDirection: "column", justifyContent: "space-between", minHeight: "220px" }}>
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px", marginBottom: "12px" }}>
                  <a 
                    href={repo.html_url} 
                    target="_blank" 
                    rel="noreferrer"
                    style={{ 
                      fontSize: "1.15rem", 
                      fontWeight: 700, 
                      color: "var(--foreground)", 
                      textDecoration: "none",
                      letterSpacing: "-0.02em"
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.color = "var(--accent-primary)"}
                    onMouseLeave={(e) => e.currentTarget.style.color = "var(--foreground)"}
                  >
                    {repo.full_name}
                  </a>
                  <span className={`badge-status badge-status-${repo.is_linked ? "completed" : "pending"}`} style={{ fontSize: "0.65rem", padding: "2px 8px" }}>
                    {repo.is_linked ? "Linked" : "Inactive"}
                  </span>
                </div>
                <p style={{ color: "var(--foreground-muted)", fontSize: "0.875rem", lineHeight: "1.5", display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden", marginBottom: "20px" }}>
                  {repo.description || "No repository description provided."}
                </p>
              </div>

              <div>
                <button
                  disabled={loadingRepoId === repo.id}
                  onClick={() => handleToggleLink(repo)}
                  style={{
                    width: "100%",
                    background: repo.is_linked ? "rgba(16, 185, 129, 0.08)" : "rgba(255, 255, 255, 0.04)",
                    border: `1px solid ${repo.is_linked ? "rgba(16, 185, 129, 0.3)" : "rgba(255, 255, 255, 0.08)"}`,
                    color: repo.is_linked ? "var(--accent-success)" : "var(--foreground)",
                    padding: "10px 20px",
                    borderRadius: "8px",
                    fontWeight: 600,
                    fontSize: "0.875rem",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "8px",
                    transition: "all 0.2s ease"
                  }}
                  onMouseEnter={(e) => {
                    if (!repo.is_linked) {
                      e.currentTarget.style.background = "var(--foreground)";
                      e.currentTarget.style.color = "var(--background-base)";
                    } else {
                      e.currentTarget.style.background = "rgba(16, 185, 129, 0.15)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!repo.is_linked) {
                      e.currentTarget.style.background = "rgba(255, 255, 255, 0.04)";
                      e.currentTarget.style.color = "var(--foreground)";
                    } else {
                      e.currentTarget.style.background = "rgba(16, 185, 129, 0.08)";
                    }
                  }}
                >
                  {loadingRepoId === repo.id ? (
                    <span style={{ fontSize: "0.85rem", opacity: 0.8 }}>Updating...</span>
                  ) : repo.is_linked ? (
                    "Audit Enabled (Disable)"
                  ) : (
                    "Enable Webhook Audits"
                  )}
                </button>
              </div>
            </div>
          ))
        )}
      </section>
    </main>
  );
}
