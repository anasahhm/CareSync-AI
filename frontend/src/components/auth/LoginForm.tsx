"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Eye, EyeOff, Mail, Lock } from "lucide-react";
import { motion } from "framer-motion";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { setAuthCookie } from "@/lib/auth-cookies";
import { Input } from "@/components/ui/Input";
import type { AuthUser } from "@/types";

export function LoginForm() {
  const router = useRouter();
  const { setAuth } = useAuthStore();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !password) return;

    setLoading(true);
    setError("");

    try {
      const { data } = await authApi.login(email, password);
      setAuth(data.user as AuthUser, data.access_token, data.refresh_token);

      // Set cookie for Next.js middleware so protected routes survive refresh.
      setAuthCookie(data.access_token);

      const redirectParam = new URLSearchParams(window.location.search).get("redirect");
      const redirectTo = redirectParam?.startsWith("/") ? redirectParam : "/dashboard";
      router.push(redirectTo);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Invalid email or password";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="w-full max-w-sm mx-auto"
    >
      {/* Wordmark */}
      <div className="flex flex-col items-start gap-2 mb-8">
        <span className="cs-logo">
          CareSync<span className="cs-logo-tag">AI</span>
        </span>
        <h1 className="cs-role-name text-white/90">Sign in</h1>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Input
          label="Email"
          type="email"
          placeholder="you@hospital.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          leftIcon={<Mail className="w-4 h-4" />}
          className="rounded-[4px]"
          autoComplete="email"
          required
        />

        <Input
          label="Password"
          type={showPassword ? "text" : "password"}
          placeholder="••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          leftIcon={<Lock className="w-4 h-4" />}
          className="rounded-[4px]"
          rightElement={
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              className="text-white/30 hover:text-white/60 transition-colors"
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          }
          autoComplete="current-password"
          required
        />

        {error && (
          <motion.p
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            className="font-mono text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-[4px] px-3 py-2"
          >
            {error}
          </motion.p>
        )}

        <button type="submit" disabled={loading} className="cs-btn cs-btn-block mt-2">
          {loading ? (
            <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
          ) : (
            <span className="cs-plus">+</span>
          )}
          {loading ? "signing in…" : "sign in"}
        </button>
      </form>

      <div className="mt-6 flex flex-col gap-3">
        <div className="flex items-center gap-3">
          <div className="flex-1 h-px bg-[#1a1a28]" />
          <span className="font-mono text-[0.65rem] uppercase tracking-[0.2em] text-white/20">or</span>
          <div className="flex-1 h-px bg-[#1a1a28]" />
        </div>
        <p className="text-center text-sm text-white/40">
          Don&apos;t have an account?{" "}
          <Link href="/auth/register" className="text-[var(--gm-accent)] hover:opacity-80 transition-opacity">
            Create one
          </Link>
        </p>
      </div>
    </motion.div>
  );
}