"use client";

import React, { useEffect, useRef } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { getDashboardRoute } from "@/lib/roles";
import {
  ShieldCheck,
  FileCheck2,
  Lock,
  ArrowRight,
  Building2,
  CheckCircle2,
  Sparkles,
  Scale,
  Shield,
  Activity,
  Award,
} from "lucide-react";

export default function HomePage() {
  const { user, loading } = useAuth();
  const portalRoute = user ? getDashboardRoute(user.role) : "/login";
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // 3D Compliance Verification Particles Animation Canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = canvas.offsetWidth || window.innerWidth);
    let height = (canvas.height = canvas.offsetHeight || 600);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = canvas.offsetWidth || window.innerWidth;
      height = canvas.height = canvas.offsetHeight || 600;
    };
    window.addEventListener("resize", handleResize);

    // Create 3D Nodes
    const numParticles = Math.min(Math.floor(width / 22), 65);
    interface Particle {
      x: number;
      y: number;
      z: number;
      vx: number;
      vy: number;
      vz: number;
      size: number;
      color: string;
      pulse: number;
    }

    const particles: Particle[] = [];
    const colors = ["#06b6d4", "#22d3ee", "#10b981", "#34d399", "#ffffff", "#8fe3cf"];

    for (let i = 0; i < numParticles; i++) {
      particles.push({
        x: (Math.random() - 0.5) * width * 1.4,
        y: (Math.random() - 0.5) * height * 1.4,
        z: Math.random() * 800 + 100,
        vx: (Math.random() - 0.5) * 0.45,
        vy: (Math.random() - 0.5) * 0.45,
        vz: (Math.random() - 0.5) * 0.6,
        size: Math.random() * 2.5 + 1.2,
        color: colors[Math.floor(Math.random() * colors.length)],
        pulse: Math.random() * Math.PI * 2,
      });
    }

    const focalLength = 400;

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      const cx = width / 2;
      const cy = height / 2;

      // Project 3D to 2D
      const projected = particles.map((p) => {
        p.x += p.vx;
        p.y += p.vy;
        p.z += p.vz;
        p.pulse += 0.03;

        // Boundary bounce inside 3D volume
        if (Math.abs(p.x) > width * 0.75) p.vx *= -1;
        if (Math.abs(p.y) > height * 0.75) p.vy *= -1;
        if (p.z < 50 || p.z > 900) p.vz *= -1;

        const scale = focalLength / p.z;
        const x2d = cx + p.x * scale;
        const y2d = cy + p.y * scale;
        const r2d = Math.max(p.size * scale, 0.8);

        return { particle: p, x: x2d, y: y2d, r: r2d, scale };
      });

      // Render 3D verification network lines
      for (let i = 0; i < projected.length; i++) {
        for (let j = i + 1; j < projected.length; j++) {
          const p1 = projected[i];
          const p2 = projected[j];

          const dx = p1.x - p2.x;
          const dy = p1.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 135) {
            const alpha = (1 - dist / 135) * 0.22 * Math.min(p1.scale, p2.scale);
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle =
              p1.particle.color === "#10b981" || p2.particle.color === "#34d399"
                ? `rgba(52, 211, 153, ${alpha})`
                : `rgba(34, 211, 238, ${alpha})`;
            ctx.lineWidth = 0.8 * Math.min(p1.scale, 1.2);
            ctx.stroke();
          }
        }
      }

      // Render Glowing Nodes
      projected.forEach((p) => {
        const pulseFactor = Math.sin(p.particle.pulse) * 0.25 + 1;
        const finalRadius = p.r * pulseFactor;

        // Radial glow
        const gradient = ctx.createRadialGradient(
          p.x,
          p.y,
          0,
          p.x,
          p.y,
          finalRadius * 3.5
        );
        gradient.addColorStop(0, p.particle.color);
        gradient.addColorStop(1, "transparent");

        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(p.x, p.y, finalRadius * 3.5, 0, Math.PI * 2);
        ctx.fill();

        // Solid core
        ctx.fillStyle = "#ffffff";
        ctx.beginPath();
        ctx.arc(p.x, p.y, Math.max(finalRadius * 0.6, 0.6), 0, Math.PI * 2);
        ctx.fill();
      });

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener("resize", handleResize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-[#040711] text-slate-100 selection:bg-cyan-500 selection:text-white">
      {/* Top Navigation Bar — Navy Glass + Cyan/Emerald Glow */}
      <header className="navbar-gradient-border sticky top-0 z-40 bg-[#040711]/85 backdrop-blur-xl border-b border-cyan-500/15">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-600 to-emerald-500 text-white shadow-lg glow-cyan">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <span className="font-extrabold text-lg tracking-tight text-white flex items-center gap-1.5">
                BidVerify <span className="gradient-text-cyan-emerald font-extrabold">AI</span>
              </span>
              <span className="hidden sm:block text-[10px] text-cyan-300/80 font-medium tracking-wide uppercase">
                GeM Procurement Compliance
              </span>
            </div>
          </div>

          <nav className="flex items-center gap-2 sm:gap-3">
            {loading ? (
              <span className="text-xs text-slate-400">Loading...</span>
            ) : user ? (
              <Link
                href={portalRoute}
                className="inline-flex items-center gap-1.5 rounded-xl btn-cyan-emerald px-4 py-2 text-xs font-bold text-slate-950 shadow-lg transition-all"
              >
                Go to {user.role === "PROCUREMENT_OFFICER" ? "Procurement" : user.role === "BIDDER" ? "Bidder" : "Admin"} Portal
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            ) : (
              <>
                <Link
                  href="/login"
                  className="rounded-xl px-4 py-2 text-xs font-semibold text-slate-200 hover:text-white hover:bg-slate-800/60 border border-slate-800 transition-all"
                >
                  Sign In
                </Link>
                <Link
                  href="/signup"
                  className="inline-flex items-center justify-center rounded-xl btn-cyan-emerald px-4 py-2 text-xs font-bold text-slate-950 shadow-md transition-all"
                >
                  Get Started
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      {/* Hero Section with Interactive 3D Particles */}
      <main className="flex-1">
        <section className="relative overflow-hidden pt-12 pb-16 sm:pt-20 sm:pb-24">
          {/* 3D Verification Particle Canvas */}
          <canvas
            ref={canvasRef}
            className="absolute inset-0 w-full h-full pointer-events-none z-0 opacity-80"
          />

          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10 space-y-6">
            {/* Tag pill */}
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-950/40 px-4 py-1.5 text-xs font-semibold text-cyan-300 shadow-lg backdrop-blur-md">
              <Sparkles className="h-3.5 w-3.5 text-emerald-400 animate-subtle-pulse" />
              <span>Government e-Marketplace (GeM) AI Compliance Suite</span>
            </div>

            <div className="space-y-4 max-w-4xl mx-auto">
              <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-tight">
                AI-Powered Integrated <br className="hidden sm:inline" />
                <span className="gradient-text-cyan-emerald">Bid Compliance Verification</span>
              </h1>
              <p className="text-sm sm:text-base text-slate-300 max-w-2xl mx-auto leading-relaxed">
                Streamline procurement eligibility, automate statutory audits, and accelerate tender evaluations with instant intelligent rule verification.
              </p>
            </div>

            {/* Role Portals Selection Cards — Nexora Navy & Cyan/Emerald Styling */}
            <div className="pt-8">
              <div className="text-xs uppercase font-bold text-cyan-300/80 tracking-widest mb-6">
                Select Your Dedicated Role Portal
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left max-w-5xl mx-auto">
                {/* 1. Bidder Portal Card (Cyan Theme) */}
                <div className="group role-card-3d glass-card rounded-2xl border border-cyan-500/25 p-7 flex flex-col justify-between shadow-2xl hover:border-cyan-400/60 transition-all duration-300">
                  <div>
                    <div className="flex items-center justify-between mb-5">
                      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-600 to-cyan-400 text-white shadow-lg glow-cyan group-hover:scale-110 transition-transform duration-300">
                        <Building2 className="h-6 w-6" />
                      </div>
                      <span className="inline-flex items-center rounded-lg bg-cyan-950/90 px-3 py-1 text-[11px] font-bold text-cyan-300 border border-cyan-500/40 tracking-wider uppercase shadow-sm">
                        Vendor Entity
                      </span>
                    </div>
                    <h3 className="text-lg font-bold text-white group-hover:text-cyan-300 transition-colors">
                      Bidder Portal
                    </h3>
                    <p className="mt-2.5 text-xs text-slate-300 leading-relaxed">
                      Discover active tenders, upload GST/PAN/MSME proof, run compliance pre-checks, and submit bids with instant feedback.
                    </p>
                  </div>

                  <div className="mt-8 pt-5 border-t border-slate-800/80 flex items-center gap-2">
                    <Link
                      href="/login/bidder"
                      className="flex-1 text-center rounded-xl btn-cyan px-4 py-2.5 text-xs font-bold text-white shadow-md transition-all"
                    >
                      Bidder Login
                    </Link>
                    <Link
                      href="/signup/bidder"
                      className="rounded-xl border border-slate-700 px-3.5 py-2.5 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800/80 transition-all"
                    >
                      Register
                    </Link>
                  </div>
                </div>

                {/* 2. Procurement Officer Portal Card (Emerald Theme) */}
                <div className="group role-card-3d glass-card rounded-2xl border border-emerald-500/25 p-7 flex flex-col justify-between shadow-2xl hover:border-emerald-400/60 transition-all duration-300">
                  <div>
                    <div className="flex items-center justify-between mb-5">
                      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 text-white shadow-lg glow-emerald group-hover:scale-110 transition-transform duration-300">
                        <FileCheck2 className="h-6 w-6" />
                      </div>
                      <span className="inline-flex items-center rounded-lg bg-emerald-950/90 px-3 py-1 text-[11px] font-bold text-emerald-300 border border-emerald-500/40 tracking-wider uppercase shadow-sm">
                        Buyer / Evaluator
                      </span>
                    </div>
                    <h3 className="text-lg font-bold text-white group-hover:text-emerald-300 transition-colors">
                      Procurement Officer
                    </h3>
                    <p className="mt-2.5 text-xs text-slate-300 leading-relaxed">
                      Publish tenders, evaluate vendor bids with automated scoring, review AI risk insights, and record official contract awards.
                    </p>
                  </div>

                  <div className="mt-8 pt-5 border-t border-slate-800/80 flex items-center gap-2">
                    <Link
                      href="/login/procurement"
                      className="flex-1 text-center rounded-xl btn-emerald px-4 py-2.5 text-xs font-bold text-white shadow-md transition-all"
                    >
                      Officer Login
                    </Link>
                    <Link
                      href="/signup/procurement"
                      className="rounded-xl border border-slate-700 px-3.5 py-2.5 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800/80 transition-all"
                    >
                      Register
                    </Link>
                  </div>
                </div>

                {/* 3. Administrator Portal Card (Cyan-Emerald Shimmer) */}
                <div className="group role-card-3d glass-card rounded-2xl border border-cyan-400/30 p-7 flex flex-col justify-between shadow-2xl hover:border-cyan-300/60 transition-all duration-300">
                  <div>
                    <div className="flex items-center justify-between mb-5">
                      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-600 to-emerald-500 text-white shadow-lg glow-cyan-emerald group-hover:scale-110 transition-transform duration-300">
                        <Lock className="h-6 w-6" />
                      </div>
                      <span className="inline-flex items-center rounded-lg bg-cyan-950/90 px-3 py-1 text-[11px] font-bold text-cyan-300 border border-cyan-400/40 tracking-wider uppercase shadow-sm">
                        System Oversight
                      </span>
                    </div>
                    <h3 className="text-lg font-bold text-white group-hover:text-cyan-300 transition-colors">
                      Administrator Portal
                    </h3>
                    <p className="mt-2.5 text-xs text-slate-300 leading-relaxed">
                      Platform governance, tamper-proof audit log inspection, organization management, and security user provisioning.
                    </p>
                  </div>

                  <div className="mt-8 pt-5 border-t border-slate-800/80 flex items-center gap-2">
                    <Link
                      href="/login/admin"
                      className="flex-1 text-center rounded-xl btn-cyan-emerald px-4 py-2.5 text-xs font-bold text-slate-950 shadow-md transition-all"
                    >
                      Admin Login
                    </Link>
                    <Link
                      href="/signup/admin"
                      className="rounded-xl border border-slate-700 px-3.5 py-2.5 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800/80 transition-all"
                    >
                      Register
                    </Link>
                  </div>
                </div>
              </div>
            </div>

            {/* Platform Feature Badges */}
            <div className="pt-8 flex flex-wrap items-center justify-center gap-4 sm:gap-6 text-xs text-slate-300">
              <div className="flex items-center gap-2 bg-slate-900/80 border border-emerald-500/30 rounded-full px-4 py-2 shadow-md backdrop-blur-md">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                <span className="text-slate-100 font-medium">Automated Statutory Verification</span>
              </div>
              <div className="flex items-center gap-2 bg-slate-900/80 border border-cyan-500/30 rounded-full px-4 py-2 shadow-md backdrop-blur-md">
                <CheckCircle2 className="h-4 w-4 text-cyan-400" />
                <span className="text-slate-100 font-medium">Dynamic Eligibility Criteria</span>
              </div>
              <div className="flex items-center gap-2 bg-slate-900/80 border border-teal-500/30 rounded-full px-4 py-2 shadow-md backdrop-blur-md">
                <CheckCircle2 className="h-4 w-4 text-teal-300" />
                <span className="text-slate-100 font-medium">Tamper-Proof Audit Trails</span>
              </div>
            </div>
          </div>
        </section>

        {/* Live Stats Counter Strip — Cyan/Emerald Theme */}
        <section className="stats-strip py-10">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
              <div className="space-y-1">
                <p className="stat-number text-3xl sm:text-4xl font-extrabold">12,480+</p>
                <p className="text-xs font-bold text-cyan-300 uppercase tracking-widest">Tenders Verified</p>
              </div>
              <div className="space-y-1">
                <p className="stat-number text-3xl sm:text-4xl font-extrabold">94,200+</p>
                <p className="text-xs font-bold text-emerald-300 uppercase tracking-widest">Compliance Audits</p>
              </div>
              <div className="space-y-1">
                <p className="stat-number text-3xl sm:text-4xl font-extrabold">3,150+</p>
                <p className="text-xs font-bold text-cyan-300 uppercase tracking-widest">Active Bidders</p>
              </div>
              <div className="space-y-1">
                <p className="stat-number text-3xl sm:text-4xl font-extrabold">&lt; 30 sec</p>
                <p className="text-xs font-bold text-emerald-300 uppercase tracking-widest">Avg. Verification Time</p>
              </div>
            </div>
          </div>
        </section>

        {/* Feature Cards Grid — Navy & White Cards with Cyan/Emerald Accents */}
        <section className="border-t border-slate-800/80 bg-[#060a17]/80 py-16 sm:py-24">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-2xl font-extrabold text-white tracking-tight sm:text-4xl">
                Platform <span className="gradient-text-cyan-emerald">Capabilities</span>
              </h2>
              <p className="mt-3 text-sm text-slate-300 max-w-xl mx-auto">
                End-to-end compliance automation powered by modern AI for GeM procurement workflows.
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {/* Card 1 */}
              <div className="glass-card rounded-2xl p-7 space-y-4 group border border-cyan-500/20">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-600 to-emerald-500 text-white shadow-lg glow-cyan group-hover:scale-110 transition-transform duration-300">
                  <FileCheck2 className="h-6 w-6" />
                </div>
                <h3 className="text-lg font-bold text-white group-hover:text-cyan-300 transition-colors">
                  Dynamic Eligibility Rules
                </h3>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Configurable criteria for turnover, local content, statutory documentation, and technical thresholds stored dynamically for each procurement tender.
                </p>
              </div>

              {/* Card 2 */}
              <div className="glass-card rounded-2xl p-7 space-y-4 group border border-emerald-500/20">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 text-white shadow-lg glow-emerald group-hover:scale-110 transition-transform duration-300">
                  <Scale className="h-6 w-6" />
                </div>
                <h3 className="text-lg font-bold text-white group-hover:text-emerald-300 transition-colors">
                  Lifecycle Governance
                </h3>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Strict multi-stage workflow governance from draft and publishing to bidding closure, evaluation, contract award, and archival.
                </p>
              </div>

              {/* Card 3 */}
              <div className="glass-card rounded-2xl p-7 space-y-4 group border border-cyan-400/20">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-600 to-teal-500 text-white shadow-lg glow-cyan group-hover:scale-110 transition-transform duration-300">
                  <Lock className="h-6 w-6" />
                </div>
                <h3 className="text-lg font-bold text-white group-hover:text-cyan-300 transition-colors">
                  Enterprise Privacy & Isolation
                </h3>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Dedicated authentication portals for Bidders, Procurement Officers, and Platform Administrators ensuring complete data privacy.
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-[#040711] py-10 text-center text-xs text-slate-400">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-600 to-emerald-500 text-white">
              <Building2 className="h-4 w-4" />
            </div>
            <span className="font-bold text-white text-sm">BidVerify AI</span>
            <span className="text-slate-400">— GeM Procurement Compliance Platform</span>
          </div>
          <div>
            <span className="text-slate-400 font-medium">Designed for Public Procurement Transparency & Statutory Compliance</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

