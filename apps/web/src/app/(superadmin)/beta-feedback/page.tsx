"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface BetaFeedback {
  id: string;
  studio_id: string;
  submitted_by: string;
  category: "bug" | "feature_request" | "usability" | "performance" | "other";
  severity: "critical" | "high" | "medium" | "low";
  body: string;
  submitted_at: string;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

interface BetaLandingToken {
  id: string;
  token: string;
  description: string | null;
  is_active: boolean;
  created_by: string;
  created_at: string;
}

const SEVERITY_COLORS: Record<BetaFeedback["severity"], "default" | "secondary" | "destructive" | "outline"> = {
  critical: "destructive",
  high: "destructive",
  medium: "secondary",
  low: "outline",
};

const CATEGORY_LABELS: Record<BetaFeedback["category"], string> = {
  bug: "Bug",
  feature_request: "Feature Request",
  usability: "Usability",
  performance: "Performance",
  other: "Other",
};

export default function BetaFeedbackPage() {
  const queryClient = useQueryClient();
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [tokenDescription, setTokenDescription] = useState("");
  const [showTokenDialog, setShowTokenDialog] = useState(false);
  const [createdToken, setCreatedToken] = useState<string | null>(null);

  const feedbackParams = new URLSearchParams();
  if (categoryFilter !== "all") feedbackParams.set("category", categoryFilter);
  if (severityFilter !== "all") feedbackParams.set("severity", severityFilter);
  const feedbackQuery = feedbackParams.toString();

  const { data: feedback = [], isLoading: feedbackLoading } = useQuery({
    queryKey: ["beta-feedback", categoryFilter, severityFilter],
    queryFn: () =>
      apiFetch<BetaFeedback[]>(
        `/admin/beta/feedback${feedbackQuery ? `?${feedbackQuery}` : ""}`
      ),
  });

  const { data: tokens = [], isLoading: tokensLoading } = useQuery({
    queryKey: ["beta-landing-tokens"],
    queryFn: () => apiFetch<BetaLandingToken[]>("/admin/beta/landing-tokens"),
  });

  const resolveMutation = useMutation({
    mutationFn: (id: string) =>
      apiFetch<BetaFeedback>(`/admin/beta/feedback/${id}/resolve`, {
        method: "POST",
        body: JSON.stringify({}),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["beta-feedback"] });
    },
  });

  const createTokenMutation = useMutation({
    mutationFn: (description: string | null) =>
      apiFetch<BetaLandingToken>("/admin/beta/landing-tokens", {
        method: "POST",
        body: JSON.stringify({ description }),
      }),
    onSuccess: (data) => {
      setCreatedToken(data.token);
      setTokenDescription("");
      queryClient.invalidateQueries({ queryKey: ["beta-landing-tokens"] });
    },
  });

  function handleCreateToken(e: React.FormEvent) {
    e.preventDefault();
    createTokenMutation.mutate(tokenDescription || null);
  }

  return (
    <div>
      <h1 className="font-display text-2xl font-bold tracking-tight">
        Beta Feedback
      </h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Manage beta program feedback and landing page access tokens.
      </p>

      <Tabs defaultValue="feedback" className="mt-6">
        <TabsList>
          <TabsTrigger value="feedback">Feedback</TabsTrigger>
          <TabsTrigger value="tokens">Landing Tokens</TabsTrigger>
        </TabsList>

        {/* Feedback Tab */}
        <TabsContent value="feedback" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Beta Feedback</CardTitle>
              <CardDescription>
                Feedback submitted by beta studio members.
              </CardDescription>

              <div className="flex gap-3 pt-2">
                <Select value={categoryFilter} onValueChange={setCategoryFilter}>
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Category" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Categories</SelectItem>
                    <SelectItem value="bug">Bug</SelectItem>
                    <SelectItem value="feature_request">Feature Request</SelectItem>
                    <SelectItem value="usability">Usability</SelectItem>
                    <SelectItem value="performance">Performance</SelectItem>
                    <SelectItem value="other">Other</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={severityFilter} onValueChange={setSeverityFilter}>
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Severity" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Severities</SelectItem>
                    <SelectItem value="critical">Critical</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="low">Low</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>

            <CardContent>
              {feedbackLoading ? (
                <p className="text-sm text-muted-foreground">Loading...</p>
              ) : feedback.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No beta feedback yet.
                </p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Category</TableHead>
                      <TableHead>Severity</TableHead>
                      <TableHead className="max-w-md">Feedback</TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {feedback.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell>
                          <Badge variant="outline">
                            {CATEGORY_LABELS[item.category]}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant={SEVERITY_COLORS[item.severity]}>
                            {item.severity}
                          </Badge>
                        </TableCell>
                        <TableCell className="max-w-md truncate">
                          {item.body}
                        </TableCell>
                        <TableCell className="whitespace-nowrap text-sm text-muted-foreground">
                          {new Date(item.submitted_at).toLocaleDateString()}
                        </TableCell>
                        <TableCell>
                          {item.resolved_at ? (
                            <Badge variant="default">Resolved</Badge>
                          ) : (
                            <Badge variant="secondary">Open</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          {!item.resolved_at && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => resolveMutation.mutate(item.id)}
                              disabled={resolveMutation.isPending}
                            >
                              Resolve
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tokens Tab */}
        <TabsContent value="tokens" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Beta Landing Tokens</CardTitle>
              <CardDescription>
                Access tokens for the private beta landing page.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleCreateToken} className="flex gap-3 mb-6">
                <Input
                  placeholder="Token description (optional)"
                  value={tokenDescription}
                  onChange={(e) => setTokenDescription(e.target.value)}
                  className="max-w-sm"
                />
                <Button
                  type="submit"
                  disabled={createTokenMutation.isPending}
                >
                  {createTokenMutation.isPending
                    ? "Creating..."
                    : "Create Token"}
                </Button>
              </form>

              {createdToken && (
                <div
                  className="mb-6 rounded-lg border border-green-200 bg-green-50 p-4 dark:border-green-800 dark:bg-green-950"
                  role="status"
                >
                  <p className="text-sm font-medium text-green-900 dark:text-green-100">
                    Token created! Share this link:
                  </p>
                  <code className="mt-1 block text-sm text-green-800 dark:text-green-200 break-all">
                    {typeof window !== "undefined"
                      ? `${window.location.origin}/beta?token=${createdToken}`
                      : `/beta?token=${createdToken}`}
                  </code>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-2"
                    onClick={() => setCreatedToken(null)}
                  >
                    Dismiss
                  </Button>
                </div>
              )}

              {tokensLoading ? (
                <p className="text-sm text-muted-foreground">Loading...</p>
              ) : tokens.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No landing tokens created yet.
                </p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Token</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Created</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {tokens.map((t) => (
                      <TableRow key={t.id}>
                        <TableCell>
                          <code className="text-xs">{t.token.slice(0, 12)}...</code>
                        </TableCell>
                        <TableCell>
                          {t.description ?? (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <Badge variant={t.is_active ? "default" : "secondary"}>
                            {t.is_active ? "Active" : "Inactive"}
                          </Badge>
                        </TableCell>
                        <TableCell className="whitespace-nowrap text-sm text-muted-foreground">
                          {new Date(t.created_at).toLocaleDateString()}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Token creation dialog for copy */}
      <Dialog open={showTokenDialog} onOpenChange={setShowTokenDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Token Created</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Copy the beta landing URL below and share it with the invitee.
          </p>
        </DialogContent>
      </Dialog>
    </div>
  );
}
