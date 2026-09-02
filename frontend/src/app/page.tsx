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
  ShieldAlert,
  Activity,
  CheckCircle,
  Landmark,
} from "lucide-react";

export default function HomePage() {
  const { user, loading } = useAuth();
  const portalRoute = user ? getDashboardRoute(user.role) : "/login";
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // 3D Particles Animation Canvas for Light Theme (#F5F8F7)
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

    // Create 3D Nodes for Light Canvas
    const numParticles = Math.min(Math.floor(width / 24), 55);
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
    const colors = ["#059669", "#10b981", "#0d9488", "#0284c7", "#34d399"];

    for (let i = 0; i < numParticles; i++) {
      particles.push({
        x: (Math.random() - 0.5) * width * 1.3,
        y: (Math.random() - 0.5) * height * 1.3,
        z: Math.random() * 800 + 100,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        vz: (Math.random() - 0.5) * 0.5,
        size: Math.random() * 2.2 + 1.2,
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
        p.pulse += 0.025;

        if (Math.abs(p.x) > width * 0.7) p.vx *= -1;
        if (Math.abs(p.y) > height * 0.7) p.vy *= -1;
        if (p.z < 50 || p.z > 900) p.vz *= -1;

        const scale = focalLength / p.z;
        const x2d = cx + p.x * scale;
        const y2d = cy + p.y * scale;
        const r2d = Math.max(p.size * scale, 0.8);

        return { particle: p, x: x2d, y: y2d, r: r2d, scale };
      });

      // Render 3D verification network lines in subtle mint/slate
      for (let i = 0; i < projected.length; i++) {
        for (let j = i + 1; j < projected.length; j++) {
          const p1 = projected[i];
          const p2 = projected[j];

          const dx = p1.x - p2.x;
          const dy = p1.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 125) {
            const alpha = (1 - dist / 125) * 0.18 * Math.min(p1.scale, 1);
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = `rgba(16, 185, 129, ${alpha})`;
            ctx.lineWidth = 0.7 * Math.min(p1.scale, 1.2);
            ctx.stroke();
          }
        }
      }

      // Render Nodes
      projected.forEach((p) => {
        const pulseFactor = Math.sin(p.particle.pulse) * 0.2 + 1;
        const finalRadius = p.r * pulseFactor;

        ctx.fillStyle = p.particle.color;
        ctx.globalAlpha = Math.min(p.scale * 0.6, 0.5);
        ctx.beginPath();
        ctx.arc(p.x, p.y, finalRadius * 2.2, 0, Math.PI * 2);
        ctx.fill();

        ctx.globalAlpha = Math.min(p.scale, 0.9);
        ctx.fillStyle = p.particle.color;
        ctx.beginPath();
        ctx.arc(p.x, p.y, finalRadius, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1.0;
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
    <div className="min-h-screen flex flex-col bg-[#F5F8F7] text-slate-900 selection:bg-emerald-500 selection:text-white font-body relative overflow-x-hidden">
      {/* Background Ambient Gradient Blobs */}
      <div className="blob-emerald top-[-100px] left-[10%] opacity-70" />
      <div className="blob-teal top-[400px] right-[5%] opacity-60" />

      {/* Sticky White Glass Navbar */}
      <header className="glass-header-light sticky top-0 z-50 transition-all">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-18 flex items-center justify-between">
          
          {/* Logo & Indian Government Emblem Branding */}
          <div className="flex items-center gap-3">
            {/* Indian Govt Emblem / Official Badge */}
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-tr from-slate-900 to-slate-800 text-amber-400 shadow-md border border-slate-700">
              <Landmark className="h-6 w-6 text-amber-300" />
            </div>
            
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="font-heading font-bold text-xl tracking-tight text-slate-900">
                  BidVerify <span className="text-emerald-600 font-extrabold">AI</span>
                </span>
                
                {/* Small Green/Teal Pulsing Status Indicator */}
                <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-50 border border-emerald-200">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 status-indicator-pulse" />
                  <span className="text-[10px] font-semibold text-emerald-700 uppercase tracking-wider">GeM Live AI</span>
                </div>
              </div>

              <span className="text-[10px] font-semibold text-slate-500 tracking-wider uppercase">
                Govt. of India • Procurement Verification Portal
              </span>
            </div>
          </div>

          {/* Rounded Navigation Buttons */}
          <nav className="flex items-center gap-2 sm:gap-4">
            {loading ? (
              <span className="text-xs text-slate-400 font-medium">Loading...</span>
            ) : user ? (
              <Link
                href={portalRoute}
                className="inline-flex items-center gap-2 rounded-full btn-emerald-fintech px-5 py-2.5 text-xs font-bold shadow-md transition-all"
              >
                Go to {user.role === "PROCUREMENT_OFFICER" ? "Procurement" : user.role === "BIDDER" ? "Bidder" : "Admin"} Portal
                <ArrowRight className="h-4 w-4" />
              </Link>
            ) : (
              <>
                <Link
                  href="/login"
                  className="rounded-full btn-navy-outline px-5 py-2.5 text-xs font-semibold shadow-xs"
                >
                  Sign In
                </Link>
                <Link
                  href="/signup"
                  className="inline-flex items-center justify-center rounded-full btn-emerald-fintech px-5 py-2.5 text-xs font-bold shadow-md"
                >
                  Get Started
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      {/* Hero Section — Light, Spacious, Floating Cards */}
      <main className="flex-1 relative z-10">
        <section className="relative pt-12 pb-16 sm:pt-20 sm:pb-24">
          {/* Light 3D Verification Particle Canvas */}
          <canvas
            ref={canvasRef}
            className="absolute inset-0 w-full h-full pointer-events-none z-0 opacity-90"
          />

          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10 space-y-6">
            
            {/* Government Badge Pill */}
            <div className="inline-flex items-center gap-2 rounded-full bg-white border border-emerald-200/80 px-4 py-1.5 text-xs font-semibold text-emerald-800 shadow-sm">
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
              <span>Official Government e-Marketplace (GeM) AI Compliance Suite</span>
            </div>

            <div className="space-y-4 max-w-4xl mx-auto">
              <h1 className="font-heading text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-slate-900 leading-tight">
                AI-Powered Integrated <br className="hidden sm:inline" />
                <span className="gradient-text-emerald">Bid Compliance Verification</span>
              </h1>
              <p className="text-base sm:text-lg text-slate-600 max-w-2xl mx-auto leading-relaxed">
                Streamline procurement eligibility, automate statutory compliance audits, and evaluate tender bids with instant, intelligent rule verification.
              </p>
            </div>

            {/* Dedicated Role Portals Selection Cards — Spacious Floating White Cards */}
            <div className="pt-10">
              <div className="text-xs uppercase font-bold text-slate-400 tracking-widest mb-6 font-heading">
                Select Your Dedicated Role Portal
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left max-w-5xl mx-auto">
                
                {/* 1. Bidder Portal Card */}
                <div className="group floating-card rounded-3xl p-8 flex flex-col justify-between transition-all duration-300">
                  <div>
                    <div className="flex items-center justify-between mb-6">
                      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600 border border-emerald-200/80 shadow-xs group-hover:scale-110 transition-transform">
                        <Building2 className="h-6 w-6" />
                      </div>
                      <span className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-[11px] font-bold text-slate-700 tracking-wide uppercase">
                        Vendor Entity
                      </span>
                    </div>
                    <h3 className="font-heading text-xl font-bold text-slate-900 group-hover:text-emerald-600 transition-colors">
                      Bidder Portal
                    </h3>
                    <p className="mt-3 text-xs text-slate-500 leading-relaxed">
                      Discover active tenders, upload GST/PAN/MSME proof, run compliance pre-checks, and submit bids with real-time audit feedback.
                    </p>
                  </div>

                  <div className="mt-8 pt-6 border-t border-slate-100 flex items-center gap-3">
                    <Link
                      href="/login/bidder"
                      className="flex-1 text-center rounded-full btn-emerald-fintech px-4 py-2.5 text-xs font-bold shadow-sm"
                    >
                      Bidder Login
                    </Link>
                    <Link
                      href="/signup/bidder"
                      className="rounded-full btn-navy-outline px-4 py-2.5 text-xs font-semibold"
                    >
                      Register
                    </Link>
                  </div>
                </div>

                {/* 2. Procurement Officer Portal Card */}
                <div className="group floating-card rounded-3xl p-8 flex flex-col justify-between transition-all duration-300">
                  <div>
                    <div className="flex items-center justify-between mb-6">
                      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-teal-50 text-teal-600 border border-teal-200/80 shadow-xs group-hover:scale-110 transition-transform">
                        <FileCheck2 className="h-6 w-6" />
                      </div>
                      <span className="inline-flex items-center rounded-full bg-emerald-50 px-3 py-1 text-[11px] font-bold text-emerald-700 border border-emerald-200 tracking-wide uppercase">
                        Buyer / Evaluator
                      </span>
                    </div>
                    <h3 className="font-heading text-xl font-bold text-slate-900 group-hover:text-emerald-600 transition-colors">
                      Procurement Officer
                    </h3>
                    <p className="mt-3 text-xs text-slate-500 leading-relaxed">
                      Publish tenders, evaluate vendor bids with automated scoring, review AI risk insights, and record official contract awards.
                    </p>
                  </div>

                  <div className="mt-8 pt-6 border-t border-slate-100 flex items-center gap-3">
                    <Link
                      href="/login/procurement"
                      className="flex-1 text-center rounded-full btn-emerald-fintech px-4 py-2.5 text-xs font-bold shadow-sm"
                    >
                      Officer Login
                    </Link>
                    <Link
                      href="/signup/procurement"
                      className="rounded-full btn-navy-outline px-4 py-2.5 text-xs font-semibold"
                    >
                      Register
                    </Link>
                  </div>
                </div>

                {/* 3. Administrator Portal Card */}
                <div className="group floating-card rounded-3xl p-8 flex flex-col justify-between transition-all duration-300">
                  <div>
                    <div className="flex items-center justify-between mb-6">
                      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-800 border border-slate-200 shadow-xs group-hover:scale-110 transition-transform">
                        <Lock className="h-6 w-6" />
                      </div>
                      <span className="inline-flex items-center rounded-full bg-slate-900 px-3 py-1 text-[11px] font-bold text-white tracking-wide uppercase">
                        System Oversight
                      </span>
                    </div>
                    <h3 className="font-heading text-xl font-bold text-slate-900 group-hover:text-emerald-600 transition-colors">
                      Administrator Portal
                    </h3>
                    <p className="mt-3 text-xs text-slate-500 leading-relaxed">
                      Platform governance, tamper-proof audit log inspection, organization management, and security user provisioning.
                    </p>
                  </div>

                  <div className="mt-8 pt-6 border-t border-slate-100 flex items-center gap-3">
                    <Link
                      href="/login/admin"
                      className="flex-1 text-center rounded-full btn-emerald-fintech px-4 py-2.5 text-xs font-bold shadow-sm"
                    >
                      Admin Login
                    </Link>
                    <Link
                      href="/signup/admin"
                      className="rounded-full btn-navy-outline px-4 py-2.5 text-xs font-semibold"
                    >
                      Register
                    </Link>
                  </div>
                </div>
              </div>
            </div>

            {/* Platform Feature Badges */}
            <div className="pt-10 flex flex-wrap items-center justify-center gap-4 text-xs font-medium text-slate-600">
              <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-full px-4 py-2 shadow-xs">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                <span>Automated Statutory Verification</span>
              </div>
              <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-full px-4 py-2 shadow-xs">
                <CheckCircle2 className="h-4 w-4 text-teal-600" />
                <span>Dynamic Eligibility Criteria</span>
              </div>
              <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-full px-4 py-2 shadow-xs">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                <span>Tamper-Proof Audit Trails</span>
              </div>
            </div>
          </div>
        </section>

        {/* Live Stats Counter Strip — JetBrains Mono Numbers */}
        <section className="stats-strip-light py-10">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
              <div className="space-y-1">
                <p className="font-mono-score text-3xl sm:text-4xl font-extrabold text-slate-900">12,480+</p>
                <p className="text-xs font-bold text-emerald-700 uppercase tracking-widest font-heading">Tenders Verified</p>
              </div>
              <div className="space-y-1">
                <p className="font-mono-score text-3xl sm:text-4xl font-extrabold text-slate-900">94,200+</p>
                <p className="text-xs font-bold text-teal-700 uppercase tracking-widest font-heading">Compliance Audits</p>
              </div>
              <div className="space-y-1">
                <p className="font-mono-score text-3xl sm:text-4xl font-extrabold text-slate-900">3,150+</p>
                <p className="text-xs font-bold text-emerald-700 uppercase tracking-widest font-heading">Active Bidders</p>
              </div>
              <div className="space-y-1">
                <p className="font-mono-score text-3xl sm:text-4xl font-extrabold text-slate-900">&lt; 30 sec</p>
                <p className="text-xs font-bold text-teal-700 uppercase tracking-widest font-heading">Avg. Verification Time</p>
              </div>
            </div>
          </div>
        </section>

        {/* Feature Capabilities Grid — Spacious Floating Cards */}
        <section className="py-16 sm:py-24">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="font-heading text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight">
                Platform <span className="gradient-text-emerald">Capabilities</span>
              </h2>
              <p className="mt-3 text-sm text-slate-500 max-w-xl mx-auto">
                End-to-end compliance automation powered by modern AI for GeM procurement workflows.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {/* Card 1 */}
              <div className="floating-card rounded-3xl p-8 space-y-4 group">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600 border border-emerald-100 shadow-xs group-hover:scale-110 transition-transform">
                  <FileCheck2 className="h-6 w-6" />
                </div>
                <h3 className="font-heading text-lg font-bold text-slate-900 group-hover:text-emerald-600 transition-colors">
                  Dynamic Eligibility Rules
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Configurable criteria for turnover, local content, statutory documentation, and technical thresholds stored dynamically for each procurement tender.
                </p>
              </div>

              {/* Card 2 */}
              <div className="floating-card rounded-3xl p-8 space-y-4 group">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-teal-50 text-teal-600 border border-teal-100 shadow-xs group-hover:scale-110 transition-transform">
                  <Scale className="h-6 w-6" />
                </div>
                <h3 className="font-heading text-lg font-bold text-slate-900 group-hover:text-emerald-600 transition-colors">
                  Lifecycle Governance
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Strict multi-stage workflow governance from draft and publishing to bidding closure, evaluation, contract award, and archival.
                </p>
              </div>

              {/* Card 3 */}
              <div className="floating-card rounded-3xl p-8 space-y-4 group">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-800 border border-slate-200 shadow-xs group-hover:scale-110 transition-transform">
                  <Lock className="h-6 w-6" />
                </div>
                <h3 className="font-heading text-lg font-bold text-slate-900 group-hover:text-emerald-600 transition-colors">
                  Enterprise Privacy & Isolation
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Dedicated authentication portals for Bidders, Procurement Officers, and Platform Administrators ensuring complete data privacy.
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer — Soft Clean Light Design */}
      <footer className="border-t border-slate-200 bg-white py-10 text-center text-xs text-slate-500 relative z-10">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-slate-900 text-amber-400">
              <Landmark className="h-4 w-4" />
            </div>
            <span className="font-heading font-bold text-slate-900 text-sm">BidVerify AI</span>
            <span className="text-slate-400">— GeM Procurement Compliance Platform</span>
          </div>
          <div>
            <span className="text-slate-500 font-medium">Designed for Public Procurement Transparency & Statutory Compliance</span>
          </div>
        </div>
      </footer>
    </div>
  );
}


