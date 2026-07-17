"use client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function LoginPage() {
  const handleLogin = () => {
    // Redirect the browser directly to the backend login route
    window.location.href = `${API_URL}/api/v1/auth/login`;
  };

  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      minHeight: "calc(100vh - 80px)",
      padding: "20px"
    }}>
      <div className="glass-card" style={{
        maxWidth: "480px",
        width: "100%",
        padding: "48px 40px",
        textAlign: "center",
        boxShadow: "0 20px 40px rgba(0, 0, 0, 0.5), 0 0 1px rgba(255, 255, 255, 0.1) inset"
      }}>
        <div style={{
          width: "48px",
          height: "48px",
          borderRadius: "50%",
          background: "rgba(59, 130, 246, 0.15)",
          border: "1px solid rgba(59, 130, 246, 0.3)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          margin: "0 auto 24px auto",
          boxShadow: "0 0 20px rgba(59, 130, 246, 0.2)"
        }}>
          <span style={{
            width: "12px",
            height: "12px",
            background: "var(--accent-primary)",
            borderRadius: "50%",
            boxShadow: "0 0 8px var(--accent-primary)"
          }}></span>
        </div>

        <h2 style={{
          fontSize: "1.75rem",
          fontWeight: 700,
          letterSpacing: "-0.03em",
          marginBottom: "12px",
          background: "linear-gradient(135deg, #ffffff 40%, #a3a3a3 100%)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent"
        }}>
          Access CodeSentinel
        </h2>

        <p style={{
          color: "var(--foreground-muted)",
          fontSize: "0.95rem",
          lineHeight: "1.6",
          marginBottom: "36px"
        }}>
          Sign in with your GitHub account to authorize repository integrations, view pull request analysis, and configure scanners.
        </p>

        <button 
          onClick={handleLogin}
          style={{
            width: "100%",
            background: "var(--foreground)",
            color: "var(--background-base)",
            border: "none",
            borderRadius: "10px",
            padding: "14px 24px",
            fontWeight: 700,
            fontSize: "0.95rem",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "12px",
            boxShadow: "0 4px 12px rgba(255, 255, 255, 0.1)",
            transition: "transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s ease"
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = "scale(1.02)";
            e.currentTarget.style.boxShadow = "0 6px 20px rgba(255, 255, 255, 0.15)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = "scale(1)";
            e.currentTarget.style.boxShadow = "0 4px 12px rgba(255, 255, 255, 0.1)";
          }}
        >
          <svg 
            viewBox="0 0 24 24" 
            width="20" 
            height="20" 
            fill="currentColor"
            style={{ display: "inline-block" }}
          >
            <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
          </svg>
          Sign in with GitHub
        </button>
      </div>
    </div>
  );
}
