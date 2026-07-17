"use client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface UserProfile {
  username: string;
  avatar_url: string | null;
}

export default function NavProfile({ user }: { user: UserProfile | null }) {
  const handleLogout = async () => {
    try {
      await fetch(`${API_URL}/api/v1/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch (e) {
      console.error("Logout fetch error:", e);
    }
    // Redirect to login page and clear local storage if any
    window.location.href = "/login";
  };

  if (!user) {
    return (
      <a 
        href="/login" 
        style={{
          textDecoration: "none",
          fontSize: "0.85rem",
          fontWeight: 600,
          color: "var(--foreground)",
          background: "rgba(255, 255, 255, 0.05)",
          border: "1px solid var(--border-glow)",
          padding: "6px 14px",
          borderRadius: "6px",
          transition: "background 0.2s ease"
        }}
        onMouseEnter={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.1)"}
        onMouseLeave={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.05)"}
      >
        Sign In
      </a>
    );
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        {user.avatar_url ? (
          <img 
            src={user.avatar_url} 
            alt={user.username} 
            style={{ width: "28px", height: "28px", borderRadius: "50%", border: "1px solid var(--border-glow)" }}
          />
        ) : (
          <div style={{ 
            width: "28px", 
            height: "28px", 
            borderRadius: "50%", 
            background: "rgba(59, 130, 246, 0.2)", 
            display: "flex", 
            alignItems: "center", 
            justifyContent: "center",
            fontSize: "0.75rem",
            fontWeight: 700,
            color: "var(--accent-primary)"
          }}>
            {user.username.substring(0, 2).toUpperCase()}
          </div>
        )}
        <span style={{ fontSize: "0.875rem", fontWeight: 500, color: "var(--foreground)" }}>
          {user.username}
        </span>
      </div>
      <button 
        onClick={handleLogout}
        style={{
          background: "none",
          border: "none",
          color: "var(--foreground-muted)",
          cursor: "pointer",
          fontSize: "0.85rem",
          fontWeight: 500,
          transition: "color 0.2s ease"
        }}
        onMouseEnter={(e) => e.currentTarget.style.color = "var(--accent-error)"}
        onMouseLeave={(e) => e.currentTarget.style.color = "var(--foreground-muted)"}
      >
        Sign Out
      </button>
    </div>
  );
}
