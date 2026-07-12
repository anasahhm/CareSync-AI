import Link from "next/link";
import { RegisterForm } from "@/components/auth/RegisterForm";

export const metadata = {
  title: "Create Account - CareSync AI",
  description: "Join CareSync AI - contactless telemedicine",
};

export default function RegisterPage() {
  return (
    <div className="min-h-screen bg-[#060608] text-white">
      {/* ── Nav ─────────────────────────────────────────────────── */}
      <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 md:px-10 py-4 bg-[#060608]/70 backdrop-blur-xl border-b border-white/5">
        <Link href="/" className="cs-logo">
          CareSync<span className="cs-logo-tag">AI</span>
        </Link>

        <div className="flex items-center gap-2 md:gap-3 justify-end flex-1 ml-8">
          <Link href="/" className="cs-nav-link">
            <span className="cs-corner-tl" />
            <span className="cs-link-text">
              <span className="cs-link-track">
                <span>Home</span>
                <span>Home</span>
              </span>
            </span>
            <span className="cs-corner-br" />
          </Link>

          <Link href="/auth/login" className="cs-nav-link">
            <span className="cs-corner-tl" />
            <span className="cs-link-text">
              <span className="cs-link-track">
                <span>Sign in</span>
                <span>Sign in</span>
              </span>
            </span>
            <span className="cs-corner-br" />
          </Link>
        </div>
      </nav>

      {/* ── Auth shell ──────────────────────────────────────────── */}
      <div className="relative min-h-screen flex items-center justify-center p-4 pt-24">
        <div
          className="absolute inset-0 opacity-[0.015] pointer-events-none"
          style={{
            backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
            backgroundSize: "80px 80px",
          }}
        />

        <div className="relative w-full max-w-sm">
          <div className="cs-auth-card p-8">
            <span className="cs-corner-tl" />
            <RegisterForm />
            <span className="cs-corner-br" />
          </div>
          <p className="text-center font-mono text-[0.65rem] uppercase tracking-[0.2em] text-white/15 mt-6">
            CareSync AI · Contactless Telemedicine Platform
          </p>
        </div>
      </div>
    </div>
  );
}