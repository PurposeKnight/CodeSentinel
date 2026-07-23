"use client";

import { useState } from "react";
import Link from "next/link";

export interface TaskReport {
  summary?: {
    total_vulnerabilities?: number;
    critical?: number;
    high?: number;
    medium?: number;
    low?: number;
  };
  architecture_score?: number;
  performance_score?: number;
  documentation_score?: number;
  findings?: Array<{
    scanner?: string;
    vulnerability_id?: string;
    severity?: string;
    file?: string;
    line?: number;
    line_number?: number;
    description?: string;
    explanation?: string;
    recommendation?: string;
    code_fix?: string;
    test_status?: string;
    recommendations?: string[];
  }>;
}

export interface AgentTask {
  id: string;
  review_id: string;
  agent: string;
  status: string;
  reason: string | null;
  report: TaskReport | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface PullRequestReview {
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

export default function ReviewDetailClient({ review }: { review: PullRequestReview }) {
  const [activeTab, setActiveTab] = useState<"security" | "code-review" | "testing" | "documentation" | "deployment">("security");

  // Get task reports
  const securityTask = review.tasks.find((t) => t.agent === "security-agent");
  const codeReviewTask = review.tasks.find((t) => t.agent === "code-review-agent");
  const testingTask = review.tasks.find((t) => t.agent === "testing-agent");
  const docTask = review.tasks.find((t) => t.agent === "documentation-agent");
  const deployTask = review.tasks.find((t) => t.agent === "deployment-agent");

  // Helper for score color classes
  const getScoreClass = (score: number | null) => {
    if (score === null) return "score-neutral";
    return score >= 80 ? "score-high" : score >= 50 ? "score-mid" : "score-low";
  };

  return (
    <main className="main-wrapper">
      <header style={{ marginBottom: "32px" }}>
        <Link 
          href="/" 
          style={{ 
            color: "var(--foreground-muted)", 
            textDecoration: "none", 
            fontSize: "0.875rem",
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            marginBottom: "16px"
          }}
        >
          &larr; Back to Dashboard
        </Link>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px" }}>
          <div>
            <h1 style={{ fontSize: "2rem", fontWeight: 700, marginBottom: "8px" }}>
              {review.repository}
            </h1>
            <p style={{ color: "var(--foreground-muted)", fontSize: "0.95rem" }}>
              Pull Request #{review.pull_request_number} &bull; Delivery ID: <span style={{ fontFamily: "monospace" }}>{review.delivery_id || "N/A"}</span>
            </p>
          </div>
          <span className={`badge-status badge-status-${review.status}`}>
            {review.status}
          </span>
        </div>
      </header>

      {/* Grid of Scores */}
      <section className="summary-grid" style={{ marginBottom: "32px" }}>
        <div className="glass-card" style={{ padding: "20px", display: "flex", alignItems: "center", justifyItems: "center", justifyContent: "space-between" }}>
          <div>
            <div className="summary-card-label">Security Score</div>
            <div style={{ fontSize: "0.85rem", color: "var(--foreground-muted)" }}>
              {securityTask?.status || "Pending"}
            </div>
          </div>
          <div className={`score-badge-circle ${getScoreClass(review.security_score)}`}>
            {review.security_score !== null ? `${review.security_score}%` : "N/A"}
          </div>
        </div>

        <div className="glass-card" style={{ padding: "20px", display: "flex", alignItems: "center", justifyItems: "center", justifyContent: "space-between" }}>
          <div>
            <div className="summary-card-label">Performance Score</div>
            <div style={{ fontSize: "0.85rem", color: "var(--foreground-muted)" }}>
              {codeReviewTask?.status || "Pending"}
            </div>
          </div>
          <div className={`score-badge-circle ${getScoreClass(review.performance_score)}`}>
            {review.performance_score !== null ? `${review.performance_score}%` : "N/A"}
          </div>
        </div>

        <div className="glass-card" style={{ padding: "20px", display: "flex", alignItems: "center", justifyItems: "center", justifyContent: "space-between" }}>
          <div>
            <div className="summary-card-label">Architecture Score</div>
            <div style={{ fontSize: "0.85rem", color: "var(--foreground-muted)" }}>
              {codeReviewTask?.status || "Pending"}
            </div>
          </div>
          <div className={`score-badge-circle ${getScoreClass(review.architecture_score)}`}>
            {review.architecture_score !== null ? `${review.architecture_score}%` : "N/A"}
          </div>
        </div>

        <div className="glass-card" style={{ padding: "20px", display: "flex", alignItems: "center", justifyItems: "center", justifyContent: "space-between" }}>
          <div>
            <div className="summary-card-label">Documentation Score</div>
            <div style={{ fontSize: "0.85rem", color: "var(--foreground-muted)" }}>
              {docTask?.status || "Pending"}
            </div>
          </div>
          <div className={`score-badge-circle ${getScoreClass(review.documentation_score)}`}>
            {review.documentation_score !== null ? `${review.documentation_score}%` : "N/A"}
          </div>
        </div>
      </section>

      {/* Tabs Menu */}
      <section className="tabs-header">
        <button 
          onClick={() => setActiveTab("security")}
          className={`tab-btn ${activeTab === "security" ? "tab-btn-active" : ""}`}
        >
          Security Scan
        </button>
        <button 
          onClick={() => setActiveTab("code-review")}
          className={`tab-btn ${activeTab === "code-review" ? "tab-btn-active" : ""}`}
        >
          Code Quality
        </button>
        <button 
          onClick={() => setActiveTab("testing")}
          className={`tab-btn ${activeTab === "testing" ? "tab-btn-active" : ""}`}
        >
          Test Coverage
        </button>
        <button 
          onClick={() => setActiveTab("documentation")}
          className={`tab-btn ${activeTab === "documentation" ? "tab-btn-active" : ""}`}
        >
          Documentation
        </button>
        <button 
          onClick={() => setActiveTab("deployment")}
          className={`tab-btn ${activeTab === "deployment" ? "tab-btn-active" : ""}`}
        >
          Deployment Gate
        </button>
      </section>

      {/* Tab Panels */}
      <section className="glass-card" style={{ padding: "32px" }}>
        
        {/* SECURITY TAB */}
        {activeTab === "security" && (
          <div>
            <h2 style={{ fontSize: "1.25rem", marginBottom: "8px" }}>Security Scan Findings</h2>
            {!securityTask ? (
              <p style={{ color: "var(--foreground-muted)" }}>No security scan was scheduled.</p>
            ) : securityTask.status !== "completed" ? (
              <p style={{ color: "var(--foreground-muted)" }}>Task status: <strong>{securityTask.status}</strong>. {securityTask.reason}</p>
            ) : (
              <div>
                <div style={{ display: "flex", gap: "24px", marginBottom: "24px", flexWrap: "wrap", padding: "16px", background: "rgba(255, 255, 255, 0.02)", borderRadius: "8px" }}>
                  <div>Total Issues: <strong>{securityTask.report?.summary?.total_vulnerabilities || 0}</strong></div>
                  <div style={{ color: "var(--accent-error)" }}>Critical: <strong>{securityTask.report?.summary?.critical || 0}</strong></div>
                  <div style={{ color: "var(--accent-warning)" }}>High: <strong>{securityTask.report?.summary?.high || 0}</strong></div>
                  <div style={{ color: "var(--accent-primary)" }}>Medium: <strong>{securityTask.report?.summary?.medium || 0}</strong></div>
                  <div style={{ color: "var(--foreground-muted)" }}>Low: <strong>{securityTask.report?.summary?.low || 0}</strong></div>
                </div>

                {(!securityTask.report?.findings || securityTask.report.findings.length === 0) ? (
                  <p style={{ color: "var(--accent-success)", fontWeight: 500 }}>Clean run! No security findings detected.</p>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
                    {securityTask.report.findings.map((f, idx) => (
                      <div key={idx} style={{ padding: "20px", border: "1px solid var(--border-glow)", borderRadius: "12px", background: "rgba(255, 255, 255, 0.01)" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                          <span style={{ fontWeight: 600, color: "var(--accent-primary)", fontSize: "0.95rem" }}>
                            {f.scanner?.toUpperCase()} &bull; {f.vulnerability_id}
                          </span>
                          <span className={`badge-status badge-status-${f.severity?.toLowerCase() === 'critical' ? 'failed' : f.severity?.toLowerCase() === 'high' ? 'failed' : f.severity?.toLowerCase() === 'medium' ? 'running' : 'pending'}`}>
                            {f.severity}
                          </span>
                        </div>
                        
                        <div style={{ fontSize: "0.9rem", color: "var(--foreground-muted)", marginBottom: "8px" }}>
                          File: <span style={{ fontFamily: "monospace", color: "var(--foreground)" }}>{f.file}</span> (Line {f.line || f.line_number || "N/A"})
                        </div>

                        {f.description && (
                          <p style={{ fontSize: "0.95rem", marginBottom: "12px" }}>{f.description}</p>
                        )}

                        <div style={{ margin: "16px 0", padding: "14px", background: "rgba(0,0,0,0.2)", borderRadius: "8px", borderLeft: "3px solid var(--accent-primary)" }}>
                          <h4 style={{ fontSize: "0.85rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--foreground-muted)", marginBottom: "4px" }}>Explanation</h4>
                          <p style={{ fontSize: "0.95rem" }}>{f.explanation}</p>
                        </div>

                        <div style={{ margin: "16px 0", padding: "14px", background: "rgba(0,0,0,0.2)", borderRadius: "8px", borderLeft: "3px solid var(--accent-success)" }}>
                          <h4 style={{ fontSize: "0.85rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--foreground-muted)", marginBottom: "4px" }}>Recommendation</h4>
                          <p style={{ fontSize: "0.95rem" }}>{f.recommendation}</p>
                        </div>

                        {f.code_fix && (
                          <div className="code-block-wrapper">
                            <div className="code-block-header">Recommended Fix</div>
                            <pre className="code-pre"><code className="code-style">{f.code_fix}</code></pre>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* CODE REVIEW TAB */}
        {activeTab === "code-review" && (
          <div>
            <h2 style={{ fontSize: "1.25rem", marginBottom: "16px" }}>Code Quality Review</h2>
            {!codeReviewTask ? (
              <p style={{ color: "var(--foreground-muted)" }}>No code review analysis was scheduled.</p>
            ) : codeReviewTask.status !== "completed" ? (
              <p style={{ color: "var(--foreground-muted)" }}>Task status: <strong>{codeReviewTask.status}</strong>. {codeReviewTask.reason}</p>
            ) : (
              <div>
                <div style={{ display: "flex", gap: "24px", marginBottom: "24px", flexWrap: "wrap", padding: "16px", background: "rgba(255, 255, 255, 0.02)", borderRadius: "8px" }}>
                  <div>Architecture Rating: <strong>{codeReviewTask.report?.architecture_score || 100}/100</strong></div>
                  <div>Performance Rating: <strong>{codeReviewTask.report?.performance_score || 100}/100</strong></div>
                </div>

                {(!codeReviewTask.report?.findings || codeReviewTask.report.findings.length === 0) ? (
                  <p style={{ color: "var(--accent-success)", fontWeight: 500 }}>No issues found! Code quality meets clean architecture standards.</p>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                    {codeReviewTask.report.findings.map((f, idx) => (
                      <div key={idx} style={{ padding: "16px", border: "1px solid var(--border-glow)", borderRadius: "10px", background: "rgba(255, 255, 255, 0.01)" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                          <span style={{ fontWeight: 600, color: "var(--foreground)" }}>
                            {f.file} {f.line ? `(Line ${f.line})` : ""}
                          </span>
                        </div>
                        <p style={{ fontSize: "0.95rem", marginBottom: "8px", color: "#e5e7eb" }}><strong>Finding:</strong> {f.explanation}</p>
                        <p style={{ fontSize: "0.95rem", color: "var(--foreground-muted)" }}><strong>Recommendation:</strong> {f.recommendation}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* TESTING TAB */}
        {activeTab === "testing" && (
          <div>
            <h2 style={{ fontSize: "1.25rem", marginBottom: "16px" }}>Test Quality Analysis</h2>
            {!testingTask ? (
              <p style={{ color: "var(--foreground-muted)" }}>No test analysis task was scheduled.</p>
            ) : testingTask.status !== "completed" ? (
              <p style={{ color: "var(--foreground-muted)" }}>Task status: <strong>{testingTask.status}</strong>. {testingTask.reason}</p>
            ) : (
              <div>
                {(!testingTask.report?.findings || testingTask.report.findings.length === 0) ? (
                  <p style={{ color: "var(--accent-success)", fontWeight: 500 }}>Your test suite provides adequate coverage.</p>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                    {testingTask.report.findings.map((f, idx) => (
                      <div key={idx} style={{ padding: "16px", border: "1px solid var(--border-glow)", borderRadius: "10px", background: "rgba(255, 255, 255, 0.01)" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                          <span style={{ fontWeight: 600, color: "var(--foreground)" }}>{f.file}</span>
                          <span className={`badge-status badge-status-${f.test_status === 'adequate' ? 'completed' : f.test_status === 'partial' ? 'running' : 'failed'}`}>
                            Coverage: {f.test_status}
                          </span>
                        </div>
                        {f.recommendations && f.recommendations.length > 0 && (
                          <div style={{ marginTop: "12px" }}>
                            <strong style={{ fontSize: "0.9rem", color: "var(--foreground-muted)" }}>Recommended Test Cases:</strong>
                            <ul style={{ listStyleType: "disc", paddingLeft: "20px", marginTop: "4px", fontSize: "0.95rem" }}>
                              {f.recommendations.map((rec: string, rIdx: number) => (
                                <li key={rIdx} style={{ marginBottom: "4px" }}>{rec}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* DOCUMENTATION TAB */}
        {activeTab === "documentation" && (
          <div>
            <h2 style={{ fontSize: "1.25rem", marginBottom: "16px" }}>Documentation & Docstring Gaps</h2>
            {!docTask ? (
              <p style={{ color: "var(--foreground-muted)" }}>No documentation task was scheduled.</p>
            ) : docTask.status !== "completed" ? (
              <p style={{ color: "var(--foreground-muted)" }}>Task status: <strong>{docTask.status}</strong>. {docTask.reason}</p>
            ) : (
              <div>
                <div style={{ display: "flex", gap: "24px", marginBottom: "24px", flexWrap: "wrap", padding: "16px", background: "rgba(255, 255, 255, 0.02)", borderRadius: "8px" }}>
                  <div>Documentation Quality: <strong>{docTask.report?.documentation_score || 100}/100</strong></div>
                </div>

                {(!docTask.report?.findings || docTask.report.findings.length === 0) ? (
                  <p style={{ color: "var(--accent-success)", fontWeight: 500 }}>All files and modules are thoroughly documented.</p>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                    {docTask.report.findings.map((f, idx) => (
                      <div key={idx} style={{ padding: "16px", border: "1px solid var(--border-glow)", borderRadius: "10px", background: "rgba(255, 255, 255, 0.01)" }}>
                        <div style={{ fontWeight: 600, color: "var(--foreground)", marginBottom: "8px" }}>{f.file}</div>
                        <p style={{ fontSize: "0.95rem", marginBottom: "8px" }}><strong>Gaps:</strong> {f.explanation}</p>
                        <p style={{ fontSize: "0.95rem", color: "var(--foreground-muted)" }}><strong>Recommendation:</strong> {f.recommendation}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* DEPLOYMENT TAB */}
        {activeTab === "deployment" && (
          <div>
            <h2 style={{ fontSize: "1.25rem", marginBottom: "16px" }}>Deployment Gate</h2>
            {!deployTask ? (
              <p style={{ color: "var(--foreground-muted)" }}>No deployment task has been initialized yet.</p>
            ) : deployTask.status === "pending" || deployTask.status === "running" ? (
              <div>
                <p style={{ color: "var(--foreground-muted)", marginBottom: "16px" }}>
                  Task Status: <strong style={{ textTransform: "capitalize" }}>{deployTask.status}</strong>
                </p>
                <div style={{ display: "flex", alignItems: "center", gap: "12px", padding: "16px", background: "rgba(255, 255, 255, 0.02)", borderRadius: "8px" }}>
                  <span className="pulsing-indicator" style={{ background: "var(--accent-warning)" }}></span>
                  <span>{deployTask.reason || "Deployment and health verification in progress..."}</span>
                </div>
              </div>
            ) : deployTask.status === "failed" ? (
              <div>
                <p style={{ color: "var(--accent-error)", fontWeight: 600, marginBottom: "12px" }}>
                  Deployment Gate Blocked
                </p>
                <p style={{ color: "var(--foreground)", marginBottom: "20px" }}>
                  {deployTask.reason || "Gate criteria not met."}
                </p>
                {deployTask.report?.rollback && (
                  <div style={{ padding: "16px", background: "rgba(239, 68, 68, 0.05)", border: "1px solid rgba(239, 68, 68, 0.2)", borderRadius: "8px" }}>
                    <strong style={{ display: "block", color: "var(--accent-error)", marginBottom: "4px" }}>Automatic Rollback Status:</strong>
                    <p style={{ fontSize: "0.9rem", color: "var(--foreground-muted)" }}>{deployTask.report.rollback}</p>
                  </div>
                )}
              </div>
            ) : (
              <div>
                <div style={{ display: "flex", gap: "24px", marginBottom: "24px", flexWrap: "wrap", padding: "16px", background: "rgba(16, 185, 129, 0.05)", border: "1px solid rgba(16, 185, 129, 0.2)", borderRadius: "8px" }}>
                  <div style={{ color: "var(--accent-success)" }}>Status: <strong>Released & Healthy</strong></div>
                  <div>Environment: <strong>{deployTask.report?.environment || "staging"}</strong></div>
                  <div>ID: <strong style={{ fontFamily: "monospace" }}>{deployTask.report?.deployment_id || "N/A"}</strong></div>
                </div>

                <div style={{ marginBottom: "20px" }}>
                  <h4 style={{ fontSize: "0.9rem", color: "var(--foreground-muted)", marginBottom: "6px" }}>Staging URL</h4>
                  {deployTask.report?.url ? (
                    <a 
                      href={deployTask.report.url} 
                      target="_blank" 
                      rel="noreferrer"
                      style={{ color: "var(--accent-primary)", fontWeight: 600, textDecoration: "none" }}
                    >
                      {deployTask.report.url} &rarr;
                    </a>
                  ) : (
                    <span style={{ color: "var(--foreground-muted)" }}>N/A</span>
                  )}
                </div>

                <div style={{ padding: "14px", background: "rgba(0,0,0,0.2)", borderRadius: "8px", borderLeft: "3px solid var(--accent-success)" }}>
                  <h4 style={{ fontSize: "0.85rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--foreground-muted)", marginBottom: "4px" }}>Verification Details</h4>
                  <p style={{ fontSize: "0.95rem" }}>{deployTask.report?.details || "All checks complete."}</p>
                </div>
              </div>
            )}
          </div>
        )}

      </section>
    </main>
  );
}
