"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { motion, useScroll, useTransform } from "framer-motion";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import {
  Hand,
  BrainCircuit,
  Shield,
  Zap,
  Video,
  ArrowRight,
  HeartPulse,
  Stethoscope,
  Lock,
} from "lucide-react";
import AsciiHandBackground from "@/components/landing/AsciiHandBackground";
import styles from "./page.module.css";

const FEATURES = [
  {
    icon: Hand,
    title: "Gesture Control",
    description:
      "MediaPipe-powered hand tracking lets patients and doctors communicate without touching any surface. Reduce cross-contamination completely.",
    color: "blue",
    badge: "Zero Touch",
  },
  {
    icon: BrainCircuit,
    title: "AI Medical Reports",
    description:
      "After every consultation, our AI synthesises doctor notes, body annotations, and patient gestures into a structured clinical report.",
    color: "purple",
    badge: "Claude AI",
  },
  {
    icon: Video,
    title: "WebRTC Consultation",
    description:
      "Peer-to-peer encrypted video calls with real-time annotation overlays. Doctors mark body areas and patients see them instantly.",
    color: "teal",
    badge: "E2E Encrypted",
  },
  {
    icon: Shield,
    title: "HIPAA-Inspired Security",
    description:
      "JWT authentication, RBAC, encrypted records, rate limiting, and audit logging at every layer of the stack.",
    color: "green",
    badge: "Enterprise",
  },
];

const GESTURES = [
  { emoji: "✌️", name: "Peace Sign", action: "Call Nurse", role: "Patient" },
  { emoji: "☝️", name: "Pointing", action: "Mark Body Area", role: "Doctor" },
  { emoji: "👍", name: "Thumbs Up", action: "Feeling Good", role: "Patient" },
  { emoji: "🤏", name: "Pinch", action: "Zoom In", role: "Doctor" },
  {
    emoji: "🖐️",
    name: "Open Palm",
    action: "Emergency Alert",
    role: "Patient",
  },
  { emoji: "✊", name: "Fist", action: "Clear Annotations", role: "Doctor" },
];

export default function LandingPage() {
  const heroRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ["start start", "end start"],
  });
  const heroY = useTransform(scrollYProgress, [0, 1], [0, 80]);
  const heroOpacity = useTransform(scrollYProgress, [0, 0.7], [1, 0]);

  // ── Horizontal storytelling scroll + footer reveal (layout-only) ─────────
  const horizontalWrapperRef = useRef<HTMLDivElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);
  const finalWrapperRef = useRef<HTMLDivElement>(null);
  const footerRevealRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    gsap.registerPlugin(ScrollTrigger);

    const ctx = gsap.context(() => {
      // Pin the horizontal container and drive it with vertical scroll.
      if (trackRef.current && horizontalWrapperRef.current) {
        const track = trackRef.current;

        gsap.to(track, {
          x: () => -(track.scrollWidth - window.innerWidth),
          ease: "none",
          scrollTrigger: {
            trigger: horizontalWrapperRef.current,
            start: "top top",
            end: () => "+=" + (track.scrollWidth - window.innerWidth),
            scrub: 1,
            pin: true,
            anticipatePin: 1,
            invalidateOnRefresh: true,
          },
        });
      }

      // Footer slides up from below the viewport into the bottom 75svh,
      // while the CTA stays pinned in the top 25svh.
      //
      // IMPORTANT: the pin and the slide-up tween live on the SAME
      // ScrollTrigger/timeline. Previously the pin was plain CSS
      // `position: sticky` while the slide was a separately-cached
      // ScrollTrigger — any layout shift (web fonts swapping in, etc.)
      // let the two drift out of sync, which is what caused the footer
      // to snap/slide away right when the pin released. Driving both
      // off one trigger keeps them permanently in lockstep.
      if (footerRevealRef.current && finalWrapperRef.current) {
        const tl = gsap.timeline({
          scrollTrigger: {
            trigger: finalWrapperRef.current,
            start: "top top",
            end: "+=100%",
            scrub: 1,
            pin: true,
            anticipatePin: 1,
            invalidateOnRefresh: true,
          },
        });

        tl.fromTo(
          footerRevealRef.current,
          { yPercent: 100 },
          { yPercent: 0, ease: "power2.out" },
        );
      }
    });

    // Web fonts loading in after mount can reflow the page and leave
    // cached ScrollTrigger start/end positions stale. Refreshing once
    // fonts (and the full page) have settled keeps everything aligned.
    const refresh = () => ScrollTrigger.refresh();
    if (typeof document !== "undefined" && "fonts" in document) {
      document.fonts.ready.then(refresh).catch(() => {});
    }
    window.addEventListener("load", refresh);

    return () => {
      window.removeEventListener("load", refresh);
      ctx.revert();
    };
  }, []);

  const colorMap: Record<string, { border: string; text: string }> = {
    blue: { border: "border-blue-500/25", text: "text-blue-400" },
    purple: { border: "border-purple-500/25", text: "text-purple-400" },
    teal: { border: "border-teal-500/25", text: "text-teal-400" },
    green: { border: "border-emerald-500/25", text: "text-emerald-400" },
  };

  const patientSteps = [
    "Create account as Patient",
    "Describe chief complaint",
    "Wait in virtual room",
    "Show gestures to communicate",
    "Report pain 1–5 with fingers",
    "Receive AI consultation report",
  ];

  const doctorSteps = [
    "Create account as Doctor",
    "View waiting patient queue",
    "Join consultation room",
    "Use gestures to annotate body areas",
    "Add notes — AI captures everything",
    "End session → AI report auto-generated",
  ];

  const securityItems = [
    "JWT Authentication",
    "Role-based Access",
    "E2E Video Encryption",
    "Rate Limiting",
    "Audit Logging",
    "Encrypted Records",
  ];

  return (
    <div className="bg-[#060608] text-white min-h-screen overflow-x-hidden">
      {/* ── Nav ─────────────────────────────────────────────────── */}
      <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 md:px-10 py-4 bg-[#060608]/70 backdrop-blur-xl ">
        {/* Wordmark — far left */}
        <a href="#hero" className="cs-logo">
          CareSync<span className="cs-logo-tag">AI</span>
        </a>

        {/* Links + auth actions — evenly spaced, pushed to the right */}
        <div className="flex items-center gap-2 md:gap-3 justify-end flex-1 ml-8">
          <div className="hidden md:flex items-center gap-1">
            {["Features", "Gestures", "Security", "Pricing"].map((item) => (
              <a
                key={item}
                href={`#${item.toLowerCase()}`}
                className="cs-nav-link"
              >
                <span className="cs-corner-tl" />
                <span className="cs-link-text">
                  <span className="cs-link-track">
                    <span>{item}</span>
                    <span>{item}</span>
                  </span>
                </span>
                <span className="cs-corner-br" />
              </a>
            ))}
          </div>

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

          <Link href="/auth/register" className="cs-btn">
            <span className="cs-plus">+</span>get started
          </Link>
        </div>
      </nav>

      {/* ── Hero ─────────────────────────────────────────────────── */}
      <section
        ref={heroRef}
        className="relative min-h-screen flex items-center justify-center px-6 pt-20"
      >
        {/* ASCII hand animation background */}
        <AsciiHandBackground />

        {/* Ambient center glow */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[300px] h-[300px] bg-teal-600/4 rounded-full blur-3xl" />
        </div>

        {/* Grid pattern */}
        <div
          className="absolute inset-0 opacity-[0.015] pointer-events-none"
          style={{
            backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
            backgroundSize: "80px 80px",
          }}
        />

        <motion.div
          style={{ y: heroY, opacity: heroOpacity }}
          className="relative z-10 text-center max-w-4xl mx-auto"
        >
          {/* Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="font-display text-5xl md:text-7xl font-normal text-white/95 leading-[0.95] mb-6 tracking-tight"
          >
            The future of
            <br />
            <span
              className="italic"
              style={{
                background:
                  "linear-gradient(135deg, #60A5FA, #818CF8, #34D399)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}
            >
              contactless medicine
            </span>
          </motion.h1>

          {/* Subheadline */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-lg md:text-xl text-white/35 max-w-2xl mx-auto leading-relaxed mb-10 font-light"
          >
            AI-powered gesture control for hospitals. Patients communicate pain
            levels, call nurses, and request care - without touching a single
            surface. Doctors annotate, zoom, and document : hands free.
          </motion.p>

          {/* CTA buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="flex flex-wrap items-center justify-center gap-3"
          >
            <Link href="/auth/register" className="cs-btn cs-btn-lg">
              <span className="cs-plus">+</span>start for free
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link href="/auth/login" className="cs-btn cs-btn-muted cs-btn-lg">
              sign in
            </Link>
          </motion.div>
        </motion.div>
      </section>

      {/* ── Horizontal storytelling section ─────────────────────────
          Platform → Gesture Library → How it Works → Security
          Vertical wheel scroll drives horizontal translation. ────── */}
      <div ref={horizontalWrapperRef} className="relative">
        <div className="sticky top-0 h-screen overflow-hidden">
          <div ref={trackRef} className={`${styles.hsTrack} flex h-screen`}>
            {/* ── Panel 1: Features ("Platform") ───────────────────── */}
            <div
              className={`${styles.hsPanel} w-screen h-screen flex-shrink-0 overflow-y-auto flex items-center`}
            >
              <section
                id="features"
                className="relative w-full pt-24 pb-12 px-6 overflow-hidden"
              >
                {/* ghost watermark */}
                <div
                  aria-hidden
                  className="pointer-events-none absolute inset-0 flex items-center justify-center select-none"
                >
                  <span
                    className="font-display italic text-[20vw] leading-none whitespace-nowrap text-transparent"
                    style={{ WebkitTextStroke: "1px rgba(255,255,255,0.045)" }}
                  >
                    Platform
                  </span>
                </div>

                <div className="max-w-5xl mx-auto relative">
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5 }}
                    className="mb-14 flex flex-col md:flex-row md:items-end md:justify-between gap-4 border-b border-white/10 pb-6"
                  >
                    <div>
                      <p className="text-xs font-mono text-white/25 uppercase tracking-widest mb-4">
                        {"// 01 — Platform"}
                      </p>
                      <h2 className="font-display italic text-4xl md:text-5xl font-normal text-white/90">
                        Built for modern healthcare
                      </h2>
                    </div>
                    <p className="text-xs font-mono text-white/25 max-w-[220px] md:text-right leading-relaxed">
                      Four systems. One contactless workflow.
                    </p>
                  </motion.div>

                  <div>
                    {FEATURES.map(
                      ({ icon: Icon, title, description, color, badge }, i) => {
                        const c = colorMap[color];
                        return (
                          <motion.div
                            key={title}
                            initial={{ opacity: 0, y: 16 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ duration: 0.5, delay: i * 0.08 }}
                            className="group grid grid-cols-[auto_1fr] md:grid-cols-[48px_44px_1fr_auto] items-center gap-4 md:gap-8 py-6 border-b border-white/8 hover:border-white/25 transition-colors"
                          >
                            <span className="hidden md:block font-mono text-xs text-white/20 group-hover:text-white/40 transition-colors">
                              {String(i + 1).padStart(2, "0")}
                            </span>
                            <div
                              className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 border ${c.border} group-hover:scale-110 transition-transform duration-300`}
                            >
                              <Icon className={`w-4 h-4 ${c.text}`} />
                            </div>
                            <div>
                              <h3 className="text-base md:text-lg font-semibold text-white/90 mb-1.5">
                                {title}
                              </h3>
                              <p className="text-sm text-white/40 leading-relaxed max-w-xl">
                                {description}
                              </p>
                            </div>
                            <span
                              className={`hidden md:inline-block justify-self-end px-2.5 py-1 rounded-full text-[10px] font-mono border whitespace-nowrap ${c.border} ${c.text}`}
                            >
                              {badge}
                            </span>
                          </motion.div>
                        );
                      },
                    )}
                  </div>
                </div>
              </section>
            </div>

            {/* ── Panel 2: Gesture Library ─────────────────────────── */}
            <div
              className={`${styles.hsPanel} w-screen h-screen flex-shrink-0 overflow-y-auto flex items-center`}
            >
              <section
                id="gestures"
                className="relative w-full pt-24 pb-12 px-6 overflow-hidden bg-gradient-to-b from-transparent via-[#08080f] to-transparent"
              >
                <div
                  aria-hidden
                  className="pointer-events-none absolute inset-0 flex items-center justify-center select-none"
                >
                  <span
                    className="font-display italic text-[16vw] leading-none whitespace-nowrap text-transparent"
                    style={{ WebkitTextStroke: "1px rgba(255,255,255,0.045)" }}
                  >
                    Gestures
                  </span>
                </div>

                <div className="max-w-5xl mx-auto relative">
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5 }}
                    className="mb-14 border-b border-white/10 pb-6"
                  >
                    <p className="text-xs font-mono text-white/25 uppercase tracking-widest mb-4">
                      {"// 02 — Gesture Library"}
                    </p>
                    <h2 className="font-display italic text-4xl md:text-5xl font-normal text-white/90 mb-4">
                      Show, don&apos;t touch
                    </h2>
                    <p className="text-white/35 max-w-xl">
                      12 distinct gestures recognised in real-time using
                      MediaPipe with temporal smoothing.
                    </p>
                  </motion.div>

                  <div className="grid md:grid-cols-2 gap-x-16">
                    {(["Patient", "Doctor"] as const).map((role) => (
                      <div key={role}>
                        <p className="flex items-center gap-2 text-xs font-mono uppercase tracking-widest mb-2">
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${role === "Doctor" ? "bg-teal-400" : "bg-blue-400"}`}
                          />
                          <span
                            className={
                              role === "Doctor"
                                ? "text-teal-400"
                                : "text-blue-400"
                            }
                          >
                            {role}
                          </span>
                        </p>
                        {GESTURES.filter((g) => g.role === role).map(
                          ({ emoji, name, action }, i) => (
                            <motion.div
                              key={name}
                              initial={{ opacity: 0, y: 12 }}
                              whileInView={{ opacity: 1, y: 0 }}
                              viewport={{ once: true }}
                              transition={{ duration: 0.4, delay: i * 0.08 }}
                              className="group flex items-center gap-5 py-5 border-b border-white/8 hover:border-white/25 transition-colors"
                            >
                              <span className="text-3xl leading-none group-hover:scale-110 group-hover:-rotate-6 transition-transform duration-300">
                                {emoji}
                              </span>
                              <div>
                                <p className="text-sm font-medium text-white/80">
                                  {name}
                                </p>
                                <p className="text-xs font-mono text-white/35 mt-0.5 uppercase tracking-wide">
                                  {action}
                                </p>
                              </div>
                            </motion.div>
                          ),
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </section>
            </div>

            {/* ── Panel 3: Workflow ("How it Works") ───────────────── */}
            <div
              className={`${styles.hsPanel} w-screen h-screen flex-shrink-0 overflow-y-auto flex items-center`}
            >
              <section className="relative w-full pt-24 pb-12 px-6 overflow-hidden">
                <div
                  aria-hidden
                  className="pointer-events-none absolute inset-0 flex items-center justify-center select-none"
                >
                  <span
                    className="font-display italic text-[16vw] leading-none whitespace-nowrap text-transparent"
                    style={{ WebkitTextStroke: "1px rgba(255,255,255,0.045)" }}
                  >
                    Workflow
                  </span>
                </div>

                <div className="max-w-5xl mx-auto relative">
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    className="mb-14 border-b border-white/10 pb-6"
                  >
                    <p className="text-xs font-mono text-white/25 uppercase tracking-widest mb-4">
                      {"// 03 — How it works"}
                    </p>
                    <h2 className="font-display italic text-4xl font-normal text-white/90">
                      From sign-in to report in minutes
                    </h2>
                  </motion.div>

                  <div className="grid md:grid-cols-2 gap-16">
                    {/* Patient flow */}
                    <motion.div
                      initial={{ opacity: 0, x: -20 }}
                      whileInView={{ opacity: 1, x: 0 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.5 }}
                    >
                      <div className="flex items-center gap-2.5 mb-10">
                        <HeartPulse className="w-4 h-4 text-blue-400" />
                        <h3 className="text-xs font-mono uppercase tracking-widest text-blue-400">
                          Patient Flow
                        </h3>
                      </div>
                      <div className="relative border-l border-blue-400/25 pl-8 space-y-9">
                        {patientSteps.map((step, i) => (
                          <div key={step} className="relative">
                            <span className="absolute -left-[35px] top-0.5 w-2 h-2 rounded-full bg-blue-400 ring-4 ring-[#060608]" />
                            <span className="block font-mono text-[10px] text-blue-400/60 mb-1">
                              {String(i + 1).padStart(2, "0")}
                            </span>
                            <p className="text-sm text-white/50 leading-relaxed">
                              {step}
                            </p>
                          </div>
                        ))}
                      </div>
                    </motion.div>

                    {/* Doctor flow */}
                    <motion.div
                      initial={{ opacity: 0, x: 20 }}
                      whileInView={{ opacity: 1, x: 0 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.5 }}
                    >
                      <div className="flex items-center gap-2.5 mb-10">
                        <Stethoscope className="w-4 h-4 text-teal-400" />
                        <h3 className="text-xs font-mono uppercase tracking-widest text-teal-400">
                          Doctor Flow
                        </h3>
                      </div>
                      <div className="relative border-l border-teal-400/25 pl-8 space-y-9">
                        {doctorSteps.map((step, i) => (
                          <div key={step} className="relative">
                            <span className="absolute -left-[35px] top-0.5 w-2 h-2 rounded-full bg-teal-400 ring-4 ring-[#060608]" />
                            <span className="block font-mono text-[10px] text-teal-400/60 mb-1">
                              {String(i + 1).padStart(2, "0")}
                            </span>
                            <p className="text-sm text-white/50 leading-relaxed">
                              {step}
                            </p>
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  </div>
                </div>
              </section>
            </div>

            {/* ── Panel 4: Security ─────────────────────────────────── */}
            <div
              className={`${styles.hsPanel} w-screen h-screen flex-shrink-0 overflow-y-auto flex items-center`}
            >
              <section
                id="security"
                className="relative w-full pt-24 pb-12 px-6 overflow-hidden bg-gradient-to-b from-transparent via-[#08080f] to-transparent"
              >
                <div
                  aria-hidden
                  className="pointer-events-none absolute inset-0 flex items-center justify-center select-none"
                >
                  <span
                    className="font-display italic text-[16vw] leading-none whitespace-nowrap text-transparent"
                    style={{ WebkitTextStroke: "1px rgba(255,255,255,0.045)" }}
                  >
                    Secure
                  </span>
                </div>

                <div className="max-w-2xl mx-auto relative">
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5 }}
                    className="text-center mb-12"
                  >
                    <p className="flex items-center justify-center gap-2 text-xs font-mono text-white/25 uppercase tracking-widest mb-4">
                      <Lock className="w-3 h-3 text-emerald-400" />
                      {"// 04 — Security"}
                    </p>
                    <h2 className="font-display italic text-4xl font-normal text-white/90 mb-4">
                      Security at every layer
                    </h2>
                    <p className="text-white/35 leading-relaxed">
                      HIPAA-inspired architecture with JWT + refresh tokens,
                      RBAC, encrypted medical records, rate limiting, audit
                      logs, and WebRTC peer-to-peer encryption.
                    </p>
                  </motion.div>

                  <div className="border-t border-white/10">
                    {securityItems.map((item, i) => (
                      <motion.div
                        key={item}
                        initial={{ opacity: 0, y: 10 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.4, delay: i * 0.06 }}
                        className="group flex items-center justify-between py-4 border-b border-white/8 hover:pl-2 transition-all duration-300"
                      >
                        <div className="flex items-center gap-4">
                          <span className="font-mono text-[10px] text-white/20">
                            {String(i + 1).padStart(2, "0")}
                          </span>
                          <span className="text-sm text-white/60 group-hover:text-white/90 transition-colors">
                            {item}
                          </span>
                        </div>
                        <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest text-emerald-400/70">
                          <Zap className="w-3 h-3" />
                          Active
                        </span>
                      </motion.div>
                    ))}
                  </div>
                </div>
              </section>
            </div>
          </div>
        </div>
      </div>

      <section
        ref={finalWrapperRef}
        className="relative"
        style={{ height: "100svh" }}
      >
        <div className="sticky top-0 h-screen overflow-hidden">
          {/* CTA — pinned in the top 45svh */}
          <div
            className="absolute top-0 left-0 right-0 z-10 flex items-center justify-center px-6"
            style={{ height: "45svh" }}
          >
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className="max-w-2xl mx-auto text-center"
            >
              <h2 className="font-display italic text-4xl md:text-5xl font-normal text-white/90 mb-4">
                Ready to transform care?
              </h2>
              <p className="text-white/35 mb-8">
                Start a free consultation today. No hardware required - just a
                webcam.
              </p>
              <div className="flex flex-wrap items-center justify-center gap-3">
                <Link href="/auth/register" className="cs-btn cs-btn-lg">
                  <span className="cs-plus">+</span>get started free
                  <ArrowRight className="w-5 h-5" />
                </Link>
              </div>
            </motion.div>
          </div>

          {/* Footer — starts below the viewport, eases up into the bottom 75svh */}
          <div
            ref={footerRevealRef}
            className={`${styles.footerReveal} absolute bottom-0 left-0 right-0`}
            style={{ height: "60svh" }}
          >
            <footer className="h-full flex items-end border-t border-white/5 px-6 md:px-16 pb-12 pt-8">
              <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-start justify-between gap-10 w-full">
                {/* ── Left: slide index / name / CTA ─────────────────────── */}
                <div className="flex-1">
                  <p className="text-xs font-mono text-white/25 uppercase tracking-widest mb-2">
                    {"// Health is Wealth"}
                  </p>
                  <h3 className="font-display italic text-4xl md:text-5xl text-white/90 mb-6">
                    CareSync<span className="text-white/40">AI</span>
                  </h3>
                  <Link
                    href="/auth/register"
                    className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-white/50 hover:text-white/90 transition-colors border border-white/10 rounded-[4px] px-4 py-2 hover:border-white/25"
                  >
                    <span className="cs-plus">+</span>Get Started
                  </Link>
                </div>

                {/* ── Right: info columns ─────────────────────────────────── */}
                <div className="flex flex-1 flex-wrap md:flex-nowrap items-start gap-8 md:gap-12">
                  <div className="flex-1 min-w-[100px]">
                    <p className="text-xs font-mono text-white/25 uppercase tracking-widest mb-3">
                      Year
                    </p>
                    <p className="text-sm text-white/60">2026</p>
                  </div>

                  <div className="flex-1 min-w-[100px]">
                    <p className="text-xs font-mono text-white/25 uppercase tracking-widest mb-3">
                      Team
                    </p>
                    <p className="text-sm text-white/60">Anas</p>
                    <p className="text-sm text-white/60">Doua</p>
                    <p className="text-sm text-white/60">Jatin</p>
                  </div>

                  <div className="flex-1 min-w-[140px]">
                    <p className="text-xs font-mono text-white/25 uppercase tracking-widest mb-3">
                      {" "}
                      {"// Contactless Care"}{" "}
                    </p>
                    <p className="text-xs text-white/30 font-mono leading-relaxed">
                      AI-generated reports are assistance only - not medical
                      diagnoses.
                    </p>
                  </div>

                  <div className="flex-1 min-w-[120px]">
                    <p className="text-xs font-mono text-white/25 uppercase tracking-widest mb-3">
                      <span className="text-emerald-400">·</span> Built for
                    </p>
                    <p className="text-sm text-white/60">AMD Hackathon 2026</p>
                    <div className="flex items-center gap-4 mt-4">
                      <Link
                        href="/auth/login"
                        className="text-xs text-white/30 hover:text-white/60 transition-colors"
                      >
                        Sign in
                      </Link>
                      <Link
                        href="/auth/register"
                        className="text-xs text-white/30 hover:text-white/60 transition-colors"
                      >
                        Register
                      </Link>
                    </div>
                  </div>
                </div>
              </div>
            </footer>
          </div>
        </div>
      </section>
    </div>
  );
}
