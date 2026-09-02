"use client";

import React, { useState } from "react";
import { RequireRole } from "@/components/auth/RequireRole";
import { Sidebar } from "@/components/layout/Sidebar";
import { MobileSidebar } from "@/components/layout/MobileSidebar";
import { TopNavbar } from "@/components/layout/TopNavbar";
import { PageHeader, BreadcrumbItem } from "@/components/layout/PageHeader";

interface DashboardLayoutProps {
  allowedRoles: string[];
  title: string;
  description?: string;
  breadcrumbs?: BreadcrumbItem[];
  action?: React.ReactNode;
  children: React.ReactNode;
}

export function DashboardLayout({
  allowedRoles,
  title,
  description,
  breadcrumbs,
  action,
  children,
}: DashboardLayoutProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <RequireRole allowedRoles={allowedRoles}>
      <div className="min-h-screen bg-slate-50 text-slate-900 flex">
        {/* Desktop Fixed Sidebar */}
        <Sidebar />

        {/* Mobile Overlay Sidebar */}
        <MobileSidebar
          isOpen={mobileMenuOpen}
          onClose={() => setMobileMenuOpen(false)}
        />

        {/* Main Content Area */}
        <div className="flex flex-1 flex-col lg:pl-64">
          {/* Top Header */}
          <TopNavbar onOpenMobileMenu={() => setMobileMenuOpen(true)} />

          {/* Page Body */}
          <main className="flex-1 px-4 py-8 sm:px-6 lg:px-8 max-w-7xl w-full mx-auto">
            <PageHeader
              title={title}
              description={description}
              breadcrumbs={breadcrumbs}
              action={action}
            />

            {children}
          </main>
        </div>
      </div>
    </RequireRole>
  );
}
