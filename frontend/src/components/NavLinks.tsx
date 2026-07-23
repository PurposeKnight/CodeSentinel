"use client";

import Link from "next/link";

export default function NavLinks({ showRepos }: { showRepos: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "32px" }}>
      <Link href="/" className="logo-link" style={{ marginRight: "8px" }}>
        <span className="pulsing-indicator"></span>
        <span className="logo-text">CODESENTINEL</span>
      </Link>
      {showRepos && (
        <div style={{ display: "flex", gap: "24px" }}>
          <Link
            href="/repositories"
            style={{
              textDecoration: "none",
              fontSize: "0.875rem",
              fontWeight: 600,
              color: "var(--foreground-muted)",
              transition: "color 0.2s ease",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "var(--foreground)")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "var(--foreground-muted)")}
          >
            Repositories
          </Link>
          <Link
            href="/monitoring"
            style={{
              textDecoration: "none",
              fontSize: "0.875rem",
              fontWeight: 600,
              color: "var(--foreground-muted)",
              transition: "color 0.2s ease",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "var(--foreground)")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "var(--foreground-muted)")}
          >
            System Health
          </Link>
        </div>
      )}
    </div>
  );
}
