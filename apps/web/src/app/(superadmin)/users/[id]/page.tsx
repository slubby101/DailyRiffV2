"use client";

import { useParams, useRouter } from "next/navigation";
import { BreadcrumbNavigation } from "@/components/breadcrumb-navigation";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { DashboardAlertBanner } from "@/components/dashboard-alert-banner";

export default function UserDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();

  return (
    <div>
      <BreadcrumbNavigation
        items={[
          { label: "Users", href: "/users" },
          { label: params.id },
        ]}
        className="mb-4"
      />

      <div className="mb-6">
        <h1 className="font-display text-3xl font-semibold tracking-tight">
          User Detail
        </h1>
        <p className="text-muted-foreground mt-1">
          <code className="font-mono text-xs">{params.id}</code>
        </p>
      </div>

      <DashboardAlertBanner variant="info" className="mb-6">
        Full user detail (email, sign-in history, role changes) requires
        Supabase Admin API integration. Impersonation and password reset will be
        wired in Slice 30.
      </DashboardAlertBanner>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>User Info</CardTitle>
            <CardDescription>
              Basic user information from auth system.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between">
              <span className="text-muted-foreground text-sm">User ID</span>
              <code className="font-mono text-xs">{params.id}</code>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Actions</CardTitle>
            <CardDescription>
              Administrative actions for this user.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button
              variant="outline"
              className="w-full"
              disabled
              title="Impersonation ships in Slice 30"
            >
              Impersonate User (Stub)
            </Button>
            <Button
              variant="outline"
              className="w-full"
              disabled
              title="Password reset ships in Slice 30"
            >
              Reset Password (Stub)
            </Button>
            <Button
              variant="destructive"
              className="w-full"
              disabled
              title="Account disable ships in Slice 30"
            >
              Disable Account (Stub)
            </Button>
            <Button
              variant="outline"
              onClick={() => router.push("/users")}
              className="w-full"
            >
              Back to Users
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
