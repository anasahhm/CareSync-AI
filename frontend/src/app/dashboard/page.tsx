"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { LogOut } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { authApi } from "@/lib/api";
import { clearAuthCookie } from "@/lib/auth-cookies";
import { PatientDashboard } from "@/components/dashboard/PatientDashboard";
import { DoctorDashboard } from "@/components/dashboard/DoctorDashboard";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";

export default function DashboardPage() {
  const { user, isAuthenticated, hasHydrated, clearAuth, refreshToken } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    if (hasHydrated && !isAuthenticated) {
      router.replace("/auth/login");
    }
  }, [hasHydrated, isAuthenticated, router]);

  async function handleLogout() {
    try {
      if (refreshToken) await authApi.logout(refreshToken);
    } catch {
      // Proceed with local logout even if server call fails
    }
    clearAuth();
    clearAuthCookie();
    router.replace("/auth/login");
  }

  if (!hasHydrated || !user) {
    return (
      <div className="min-h-screen bg-[#060608] flex items-center justify-center">
        <div className="w-5 h-5 border-2 border-blue-500/50 border-t-blue-400 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#060608]">
      {/* Ambient background */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-[600px] h-[400px] bg-blue-600/3 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-[500px] h-[400px] bg-purple-600/3 rounded-full blur-3xl" />
      </div>

      {/* Nav — matches marketing site header language */}
      <nav className="sticky top-0 z-20 flex items-center justify-between px-6 md:px-10 py-4 bg-[#060608]/70 backdrop-blur-xl border-b border-white/5">
        <a href="/dashboard" className="cs-logo">
          CareSync<span className="cs-logo-tag">AI</span>
        </a>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2.5">
            <Avatar name={user.full_name} role={user.role} size="sm" online />
            <div className="hidden sm:block leading-tight">
              <p className="text-xs text-white/70 font-medium leading-none">{user.full_name}</p>
              <p className="text-[10px] font-mono text-white/30 mt-1 uppercase tracking-widest">{user.role}</p>
            </div>
          </div>

          <Button
            variant="ghost"
            size="sm"
            leftIcon={<LogOut className="w-3.5 h-3.5" />}
            onClick={handleLogout}
            className="bg-transparent hover:bg-white/90 text-white/50 hover:text-[#060608] border border-white/10 hover:border-white/90 rounded-md font-mono text-[11px] uppercase tracking-widest"
          >
            Sign out
          </Button>
        </div>
      </nav>

      {/* Content */}
      <main className="relative z-10 px-6 md:px-10 py-10 md:py-14">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: "easeOut" }}
        >
          {user.role === "DOCTOR" || user.role === "ADMIN" ? (
            <DoctorDashboard />
          ) : (
            <PatientDashboard />
          )}
        </motion.div>
      </main>
    </div>
  );
}