"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { StudioResponse } from "@dailyriff/api-client";
import { apiFetch } from "@/lib/api";
import { BreadcrumbNavigation } from "@/components/breadcrumb-navigation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

function useStudioDetail(id: string) {
  return useQuery<StudioResponse>({
    queryKey: ["admin", "studios", id],
    queryFn: () => apiFetch(`/admin/studios/${id}`),
    enabled: !!id,
  });
}

export default function StudioDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const studio = useStudioDetail(params.id);

  const suspendMutation = useMutation({
    mutationFn: () => apiFetch(`/admin/studios/${params.id}/suspend`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "studios"] });
    },
  });

  const verifyMutation = useMutation({
    mutationFn: () => apiFetch(`/admin/studios/${params.id}/verify`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "studios"] });
    },
  });

  if (studio.isLoading) {
    return <p className="text-muted-foreground" role="status">Loading studio...</p>;
  }

  if (!studio.data) {
    return <p className="text-destructive">Studio not found.</p>;
  }

  const s = studio.data;

  return (
    <div>
      <BreadcrumbNavigation
        items={[
          { label: "Studios", href: "/studios" },
          { label: s.display_name || s.name },
        ]}
        className="mb-4"
      />

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">
            {s.display_name || s.name}
          </h1>
          <p className="text-muted-foreground mt-1">
            {s.name} &middot; {s.timezone}
          </p>
        </div>
        <Badge
          variant={
            s.state === "active"
              ? "default"
              : s.state === "suspended"
                ? "destructive"
                : "secondary"
          }
          className="text-base px-3 py-1"
        >
          {s.state}
        </Badge>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Studio Details</CardTitle>
            <CardDescription>Core information about this studio.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between">
              <span className="text-muted-foreground text-sm">ID</span>
              <code className="font-mono text-xs">{s.id}</code>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-muted-foreground text-sm">Name</span>
              <span className="text-sm">{s.name}</span>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-muted-foreground text-sm">Display Name</span>
              <span className="text-sm">{s.display_name ?? "—"}</span>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-muted-foreground text-sm">Timezone</span>
              <span className="text-sm">{s.timezone}</span>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-muted-foreground text-sm">Primary Color</span>
              <span className="text-sm">
                {s.primary_color ? (
                  <span className="flex items-center gap-2">
                    <span
                      className="inline-block h-4 w-4 rounded-sm border border-border"
                      style={{ backgroundColor: s.primary_color }}
                      aria-hidden="true"
                    />
                    {s.primary_color}
                  </span>
                ) : (
                  "Default"
                )}
              </span>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-muted-foreground text-sm">Beta Cohort</span>
              <span className="text-sm">{s.beta_cohort ? "Yes" : "No"}</span>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-muted-foreground text-sm">Created</span>
              <span className="text-sm">
                {new Date(s.created_at).toLocaleString()}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Actions</CardTitle>
            <CardDescription>
              Administrative actions for this studio.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {s.state !== "active" && (
              <Button
                onClick={() => verifyMutation.mutate()}
                disabled={verifyMutation.isPending}
                className="w-full"
              >
                {verifyMutation.isPending ? "Verifying..." : "Verify / Activate Studio"}
              </Button>
            )}
            {s.state !== "suspended" && (
              <Button
                variant="destructive"
                onClick={() => suspendMutation.mutate()}
                disabled={suspendMutation.isPending}
                className="w-full"
              >
                {suspendMutation.isPending ? "Suspending..." : "Suspend Studio"}
              </Button>
            )}
            <Button
              variant="outline"
              className="w-full"
              disabled
              title="Impersonation service not yet implemented"
            >
              Impersonate Studio Owner (Stub)
            </Button>
            <Button
              variant="outline"
              onClick={() => router.push("/studios")}
              className="w-full"
            >
              Back to Studios
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
