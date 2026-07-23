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

  // Settings state variables
  const [selectedRepoSettings, setSelectedRepoSettings] = useState<Repository | null>(null);
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [slackWebhook, setSlackWebhook] = useState("");
  const [alertEmail, setAlertEmail] = useState("");
  const [minSecurity, setMinSecurity] = useState(70);
  const [minOverall, setMinOverall] = useState(60);
  const [enabledAgents, setEnabledAgents] = useState<string[]>([]);

  const handleOpenSettings = async (repo: Repository) => {
    setSelectedRepoSettings(repo);
    setSettingsLoading(true);
    const [owner, name] = repo.full_name.split("/");
    try {
      const res = await fetch(`${API_URL}/api/v1/repositories/${owner}/${name}/settings`, {
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        setSlackWebhook(data.slack_webhook_url || "");
        setAlertEmail(data.alert_email || "");
        setMinSecurity(data.min_security_score ?? 70);
        setMinOverall(data.min_overall_score ?? 60);
        setEnabledAgents(data.enabled_agents || []);
      }
    } catch (e) {
      console.error("Error loading settings:", e);
    } finally {
      setSettingsLoading(false);
    }
  };

  const handleSaveSettings = async () => {
    if (!selectedRepoSettings) return;
    const [owner, name] = selectedRepoSettings.full_name.split("/");
    try {
      const res = await fetch(`${API_URL}/api/v1/repositories/${owner}/${name}/settings`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          slack_webhook_url: slackWebhook || null,
          alert_email: alertEmail || null,
          min_security_score: Number(minSecurity),
          min_overall_score: Number(minOverall),
          enabled_agents: enabledAgents,
        }),
        credentials: "include",
      });
      if (res.ok) {
        setSelectedRepoSettings(null);
      } else {
        alert("Failed to save settings");
      }
    } catch (e) {
      console.error("Error saving settings:", e);
      alert("Error saving settings");
    }
  };

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

              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {repo.is_linked && (
                  <button
                    onClick={() => handleOpenSettings(repo)}
                    style={{
                      width: "100%",
                      background: "rgba(255, 255, 255, 0.02)",
                      border: "1px solid rgba(255, 255, 255, 0.08)",
                      color: "var(--foreground-muted)",
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
                      e.currentTarget.style.background = "rgba(255, 255, 255, 0.05)";
                      e.currentTarget.style.color = "var(--foreground)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = "rgba(255, 255, 255, 0.02)";
                      e.currentTarget.style.color = "var(--foreground-muted)";
                    }}
                  >
                    ⚙️ Configure Settings
                  </button>
                )}
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

      {/* Settings Modal overlay */}
      {selectedRepoSettings && (
        <div style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: "rgba(0, 0, 0, 0.7)",
          backdropFilter: "blur(8px)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 1000,
          padding: "20px"
        }}>
          <div className="glass-card" style={{
            width: "100%",
            maxWidth: "540px",
            padding: "36px",
            background: "rgba(20, 20, 20, 0.95)",
            border: "1px solid var(--border-glow)",
            maxHeight: "90vh",
            overflowY: "auto"
          }}>
            <h2 style={{ fontSize: "1.5rem", marginBottom: "8px", fontWeight: 700 }}>
              Repository Settings
            </h2>
            <p style={{ color: "var(--foreground-muted)", fontSize: "0.9rem", marginBottom: "24px" }}>
              Configure gating policies and integrations for <strong>{selectedRepoSettings.full_name}</strong>.
            </p>

            {settingsLoading ? (
              <p style={{ color: "var(--foreground-muted)" }}>Loading configurations...</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "var(--foreground-muted)", marginBottom: "8px" }}>
                    Slack Alert Webhook URL
                  </label>
                  <input
                    type="text"
                    value={slackWebhook}
                    onChange={(e) => setSlackWebhook(e.target.value)}
                    placeholder="https://hooks.slack.com/services/..."
                    style={{
                      width: "100%",
                      background: "rgba(255, 255, 255, 0.02)",
                      border: "1px solid rgba(255, 255, 255, 0.1)",
                      borderRadius: "6px",
                      padding: "10px 14px",
                      color: "var(--foreground)",
                      fontSize: "0.9rem"
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "var(--foreground-muted)", marginBottom: "8px" }}>
                    Alert Notification Email
                  </label>
                  <input
                    type="email"
                    value={alertEmail}
                    onChange={(e) => setAlertEmail(e.target.value)}
                    placeholder="devops@company.com"
                    style={{
                      width: "100%",
                      background: "rgba(255, 255, 255, 0.02)",
                      border: "1px solid rgba(255, 255, 255, 0.1)",
                      borderRadius: "6px",
                      padding: "10px 14px",
                      color: "var(--foreground)",
                      fontSize: "0.9rem"
                    }}
                  />
                </div>

                <div style={{ display: "flex", gap: "20px" }}>
                  <div style={{ flex: 1 }}>
                    <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "var(--foreground-muted)", marginBottom: "8px" }}>
                      Min Security Score
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={minSecurity}
                      onChange={(e) => setMinSecurity(Number(e.target.value))}
                      style={{
                        width: "100%",
                        background: "rgba(255, 255, 255, 0.02)",
                        border: "1px solid rgba(255, 255, 255, 0.1)",
                        borderRadius: "6px",
                        padding: "10px 14px",
                        color: "var(--foreground)",
                        fontSize: "0.9rem"
                      }}
                    />
                  </div>
                  <div style={{ flex: 1 }}>
                    <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "var(--foreground-muted)", marginBottom: "8px" }}>
                      Min Overall Score
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={minOverall}
                      onChange={(e) => setMinOverall(Number(e.target.value))}
                      style={{
                        width: "100%",
                        background: "rgba(255, 255, 255, 0.02)",
                        border: "1px solid rgba(255, 255, 255, 0.1)",
                        borderRadius: "6px",
                        padding: "10px 14px",
                        color: "var(--foreground)",
                        fontSize: "0.9rem"
                      }}
                    />
                  </div>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "var(--foreground-muted)", marginBottom: "12px" }}>
                    Enabled Agent Workflow
                  </label>
                  <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                    {[
                      { key: "security-agent", label: "Security Scanning (Semgrep, Trivy, Bandit, pip-audit)" },
                      { key: "code-review-agent", label: "Code Quality & Design Reviews" },
                      { key: "testing-agent", label: "Test Coverage & Missing Tests Analysis" },
                      { key: "documentation-agent", label: "Documentation & Docstring Analysis" },
                      { key: "deployment-agent", label: "Release/Deployment Gating" }
                    ].map((agent) => (
                      <label key={agent.key} style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "0.9rem", cursor: "pointer", color: "var(--foreground)" }}>
                        <input
                          type="checkbox"
                          checked={enabledAgents.includes(agent.key)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setEnabledAgents([...enabledAgents, agent.key]);
                            } else {
                              setEnabledAgents(enabledAgents.filter((a) => a !== agent.key));
                            }
                          }}
                          style={{ accentColor: "var(--accent-primary)" }}
                        />
                        <span>{agent.label}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div style={{ display: "flex", gap: "12px", marginTop: "12px", justifyContent: "flex-end" }}>
                  <button
                    onClick={() => setSelectedRepoSettings(null)}
                    style={{
                      background: "rgba(255,255,255,0.04)",
                      border: "none",
                      color: "var(--foreground)",
                      padding: "10px 20px",
                      borderRadius: "6px",
                      fontWeight: 600,
                      cursor: "pointer"
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveSettings}
                    style={{
                      background: "var(--accent-primary)",
                      border: "none",
                      color: "white",
                      padding: "10px 20px",
                      borderRadius: "6px",
                      fontWeight: 600,
                      cursor: "pointer"
                    }}
                  >
                    Save Configuration
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
