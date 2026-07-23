"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Dependency {
  status: string;
  latency_ms?: number;
  detail?: string | null;
}

interface WorkerHealth {
  [key: string]: string;
}

interface HealthData {
  status: string;
  service: string;
  version: string;
  details: {
    dependencies: {
      postgres: Dependency;
      redis: Dependency;
      rabbitmq: Dependency;
    };
    workers: WorkerHealth;
  };
}

export default function MonitoringPage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/health/detailed`, {
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        setHealth(data);
        setError(null);
      } else {
        setError(`Failed to fetch detailed system health: status ${res.status}`);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to communicate with CodeSentinel API.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <main className="main-wrapper">
      <header style={{ marginBottom: "40px" }}>
        <h1 style={{ fontSize: "2rem", marginBottom: "8px", fontWeight: 700 }}>
          System Health Monitoring
        </h1>
        <p style={{ color: "var(--foreground-muted)" }}>
          Real-time diagnostics of the CodeSentinel microservices infrastructure and task worker daemons.
        </p>
      </header>

      {loading ? (
        <p style={{ color: "var(--foreground-muted)" }}>Connecting to cluster diagnostics...</p>
      ) : error ? (
        <div className="glass-card" style={{ padding: "28px", border: "1px solid rgba(239, 68, 68, 0.2)", background: "rgba(239, 68, 68, 0.02)" }}>
          <p style={{ color: "var(--accent-error)", fontWeight: 600 }}>System Connection Error</p>
          <p style={{ color: "var(--foreground-muted)", fontSize: "0.9rem", marginTop: "4px" }}>{error}</p>
        </div>
      ) : health ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "40px" }}>
          {/* Overall Health Status Banner */}
          <div className="glass-card" style={{
            padding: "24px 32px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: health.status === "ok" ? "rgba(16, 185, 129, 0.04)" : "rgba(245, 158, 11, 0.04)",
            border: `1px solid ${health.status === "ok" ? "rgba(16, 185, 129, 0.2)" : "rgba(245, 158, 11, 0.2)"}`,
            borderRadius: "12px"
          }}>
            <div>
              <span style={{ fontSize: "0.85rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--foreground-muted)" }}>Cluster State</span>
              <h2 style={{ fontSize: "1.75rem", fontWeight: 800, marginTop: "2px", color: health.status === "ok" ? "var(--accent-success)" : "var(--accent-warning)" }}>
                {health.status === "ok" ? "ALL SYSTEMS OPERATIONAL" : "DEGRADED PERFORMANCE"}
              </h2>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <span className="pulsing-indicator" style={{ background: health.status === "ok" ? "var(--accent-success)" : "var(--accent-warning)", width: "12px", height: "12px" }}></span>
              <span style={{ fontSize: "0.9rem", fontWeight: 600 }}>v{health.version}</span>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "32px" }}>
            {/* Core Infrastructure Dependencies */}
            <div>
              <h3 style={{ fontSize: "1.15rem", fontWeight: 700, marginBottom: "16px" }}>Core Infrastructure</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                {[
                  { key: "postgres", label: "PostgreSQL Database", desc: "Configuration, reviews and tasks persistence" },
                  { key: "redis", label: "Redis Key-Value Cache", desc: "Session storage and worker heartbeats" },
                  { key: "rabbitmq", label: "RabbitMQ Message Queue", desc: "Webhook delivery and task dispatch pipeline" }
                ].map((dep) => {
                  const data = health.details.dependencies[dep.key as keyof typeof health.details.dependencies] || { status: "unavailable" };
                  const isOk = data.status === "ok" || data.status === "ready";
                  return (
                    <div key={dep.key} className="glass-card" style={{ padding: "20px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <strong style={{ display: "block", color: "var(--foreground)" }}>{dep.label}</strong>
                        <span style={{ fontSize: "0.8rem", color: "var(--foreground-muted)" }}>{dep.desc}</span>
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <span style={{
                          display: "inline-block",
                          padding: "3px 10px",
                          borderRadius: "20px",
                          fontSize: "0.75rem",
                          fontWeight: 700,
                          background: isOk ? "rgba(16, 185, 129, 0.08)" : "rgba(239, 68, 68, 0.08)",
                          color: isOk ? "var(--accent-success)" : "var(--accent-error)",
                          border: `1px solid ${isOk ? "rgba(16, 185, 129, 0.2)" : "rgba(239, 68, 68, 0.2)"}`
                        }}>
                          {isOk ? "ONLINE" : "OFFLINE"}
                        </span>
                        {data.latency_ms !== undefined && (
                          <span style={{ display: "block", fontSize: "0.75rem", color: "var(--foreground-muted)", marginTop: "4px" }}>
                            {data.latency_ms}ms latency
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Task Worker Daemons */}
            <div>
              <h3 style={{ fontSize: "1.15rem", fontWeight: 700, marginBottom: "16px" }}>Workflow Agents</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                {[
                  { key: "planner-worker", label: "Planner Coordinator Agent", desc: "Parses webhook events & schedules pipelines" },
                  { key: "security-worker", label: "Security Scanning Worker", desc: "Gitleaks, Semgrep, Trivy static audits" },
                  { key: "code-review-worker", label: "Code Quality Reviewer", desc: "Design, readability, code pattern analysis" },
                  { key: "testing-worker", label: "Testing Coverage Agent", desc: "Analyzes missing test suites & mock runs" },
                  { key: "documentation-worker", label: "Docstrings & Doc Analyzer", desc: "Validates documentation completeness" },
                  { key: "deployment-worker", label: "CI/CD Deployment Release Gate", desc: "Evaluates gates & runs staging checks" }
                ].map((worker) => {
                  const status = health.details.workers[worker.key] || "offline";
                  const isOnline = status === "online";
                  return (
                    <div key={worker.key} className="glass-card" style={{ padding: "20px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <strong style={{ display: "block", color: "var(--foreground)" }}>{worker.label}</strong>
                        <span style={{ fontSize: "0.8rem", color: "var(--foreground-muted)" }}>{worker.desc}</span>
                      </div>
                      <span style={{
                        display: "inline-block",
                        padding: "3px 10px",
                        borderRadius: "20px",
                        fontSize: "0.75rem",
                        fontWeight: 700,
                        background: isOnline ? "rgba(16, 185, 129, 0.08)" : "rgba(239, 68, 68, 0.08)",
                        color: isOnline ? "var(--accent-success)" : "var(--accent-error)",
                        border: `1px solid ${isOnline ? "rgba(16, 185, 129, 0.2)" : "rgba(239, 68, 68, 0.2)"}`
                      }}>
                        {isOnline ? "ONLINE" : "OFFLINE"}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
