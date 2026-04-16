"use client";

import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { StudioResponse } from "@dailyriff/api-client";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

function usePendingStudios() {
  return useQuery<StudioResponse[]>({
    queryKey: ["admin", "verification-queue"],
    queryFn: () => apiFetch("/admin/verification-queue"),
  });
}

export default function VerificationQueuePage() {
  const pending = usePendingStudios();
  const queryClient = useQueryClient();

  const verifyMutation = useMutation({
    mutationFn: (studioId: string) =>
      apiFetch(`/admin/studios/${studioId}/verify`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin"] });
    },
  });

  const suspendMutation = useMutation({
    mutationFn: (studioId: string) =>
      apiFetch(`/admin/studios/${studioId}/suspend`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin"] });
    },
  });

  return (
    <div>
      <div className="mb-6">
        <h1 className="font-display text-3xl font-semibold tracking-tight">
          Verification Queue
        </h1>
        <p className="text-muted-foreground mt-2">
          Review and approve pending studio registrations.
        </p>
      </div>

      {pending.isLoading ? (
        <p className="text-muted-foreground text-sm" role="status">
          Loading queue...
        </p>
      ) : (pending.data ?? []).length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">
              No studios pending verification. You&apos;re all caught up!
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {(pending.data ?? []).map((studio) => (
            <Card key={studio.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>
                      <Link
                        href={`/studios/${studio.id}`}
                        className="hover:underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring rounded-sm"
                      >
                        {studio.display_name || studio.name}
                      </Link>
                    </CardTitle>
                    <CardDescription className="mt-1">
                      {studio.name} &middot; {studio.timezone} &middot; Applied{" "}
                      {new Date(studio.created_at).toLocaleDateString()}
                    </CardDescription>
                  </div>
                  <Badge variant="secondary">{studio.state}</Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={() => verifyMutation.mutate(studio.id)}
                    disabled={verifyMutation.isPending}
                  >
                    {verifyMutation.isPending ? "Approving..." : "Approve"}
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => suspendMutation.mutate(studio.id)}
                    disabled={suspendMutation.isPending}
                  >
                    {suspendMutation.isPending ? "Rejecting..." : "Reject"}
                  </Button>
                  <Link href={`/studios/${studio.id}`}>
                    <Button variant="outline" size="sm">
                      View Details
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
