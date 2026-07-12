"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Eye, EyeOff, Mail, Lock, User, Stethoscope, HeartPulse } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { setAuthCookie } from "@/lib/auth-cookies";
import { Input } from "@/components/ui/Input";
import { cn } from "@/lib/utils";
import type { AuthUser, UserRole } from "@/types";

type Step = "role" | "details";

export function RegisterForm() {
  const router = useRouter();
  const { setAuth } = useAuthStore();

  const [step, setStep] = useState<Step>("role");
  const [role, setRole] = useState<UserRole>("PATIENT");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!fullName || !email || !password) return;

    setLoading(true);
    setError("");

    try {
      const { data } = await authApi.register({ email, password, full_name: fullName, role });
      setAuth(data.user as AuthUser, data.access_token, data.refresh_token);
      setAuthCookie(data.access_token);
      router.push("/dashboard");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Registration failed. Please try again.";
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
        <h1 className="cs-role-name text-white/90">Create account</h1>
      </div>

      <AnimatePresence mode="wait">
        {step === "role" ? (
          <motion.div
            key="role"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.25 }}
            className="flex flex-col gap-4"
          >
            <p className="cs-role-eyebrow text-white/40">I am a...</p>

            {([
              {
                value: "PATIENT" as UserRole,
                label: "Patient",
                desc: "Access consultations and health records",
                icon: HeartPulse,
                color: "blue",
              },
              {
                value: "DOCTOR" as UserRole,
                label: "Doctor / Clinician",
                desc: "Conduct gesture-controlled consultations",
                icon: Stethoscope,
                color: "teal",
              },
            ] as const).map(({ value, label, desc, icon: Icon, color }) => (
              <button
                key={value}
                type="button"
                onClick={() => setRole(value)}
                className={cn(
                  "cs-role-card flex items-start gap-4 p-4 border text-left transition-all duration-150",
                  role === value
                    ? color === "blue"
                      ? "bg-blue-500/10 border-blue-500/40"
                      : "bg-teal-500/10 border-teal-500/40"
                    : "bg-white/2 border-[#1a1a28] hover:border-[#252535]"
                )}
              >
                <div
                  className={cn(
                    "w-9 h-9 rounded-[4px] flex items-center justify-center flex-shrink-0 mt-0.5",
                    role === value
                      ? color === "blue"
                        ? "bg-blue-500/20"
                        : "bg-teal-500/20"
                      : "bg-white/5"
                  )}
                >
                  <Icon
                    className={cn(
                      "w-4 h-4",
                      role === value
                        ? color === "blue"
                          ? "text-blue-400"
                          : "text-teal-400"
                        : "text-white/30"
                    )}
                  />
                </div>
                <div>
                  <p className={cn("cs-role-name text-[1rem]", role === value ? "text-white/90" : "text-white/60")}>
                    {label}
                  </p>
                  <p className="text-xs text-white/30 mt-0.5">{desc}</p>
                </div>
              </button>
            ))}

            <button type="button" onClick={() => setStep("details")} className="cs-btn cs-btn-block mt-2">
              <span className="cs-plus">+</span>continue
            </button>
          </motion.div>
        ) : (
          <motion.form
            key="details"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.25 }}
            onSubmit={handleSubmit}
            className="flex flex-col gap-4"
          >
            <button
              type="button"
              onClick={() => setStep("role")}
              className="font-mono text-[0.7rem] uppercase tracking-[0.12em] text-white/30 hover:text-white/60 text-left transition-colors flex items-center gap-1 mb-1"
            >
              ← back
            </button>

            <Input
              label="Full Name"
              type="text"
              placeholder="Dr. Jane Smith"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              leftIcon={<User className="w-4 h-4" />}
              className="rounded-[4px]"
              autoComplete="name"
              required
            />

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
              placeholder="Min. 8 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              leftIcon={<Lock className="w-4 h-4" />}
              hint="At least 8 characters"
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
              autoComplete="new-password"
              required
              minLength={8}
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
              {loading ? "creating account…" : "create account"}
            </button>
          </motion.form>
        )}
      </AnimatePresence>

      <p className="mt-6 text-center text-sm text-white/40">
        Already have an account?{" "}
        <Link href="/auth/login" className="text-[var(--gm-accent)] hover:opacity-80 transition-opacity">
          Sign in
        </Link>
      </p>
    </motion.div>
  );
}