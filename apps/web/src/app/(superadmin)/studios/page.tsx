"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import type { StudioResponse } from "@dailyriff/api-client";
import { apiFetch } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

function useAdminStudios() {
  return useQuery<StudioResponse[]>({
    queryKey: ["admin", "studios"],
    queryFn: () => apiFetch("/admin/studios"),
  });
}

export default function StudiosPage() {
  const studios = useAdminStudios();
  const [search, setSearch] = useState("");
  const [stateFilter, setStateFilter] = useState<string>("all");

  const filtered = (studios.data ?? []).filter((s) => {
    const matchesSearch =
      !search ||
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      (s.display_name ?? "").toLowerCase().includes(search.toLowerCase());
    const matchesState = stateFilter === "all" || s.state === stateFilter;
    return matchesSearch && matchesState;
  });

  return (
    <div>
      <div className="mb-6">
        <h1 className="font-display text-3xl font-semibold tracking-tight">
          Studios
        </h1>
        <p className="text-muted-foreground mt-2">
          Manage all studios on the platform.
        </p>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <Input
          placeholder="Search studios..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm"
          aria-label="Search studios"
        />
        <Select value={stateFilter} onValueChange={setStateFilter}>
          <SelectTrigger className="w-40" aria-label="Filter by state">
            <SelectValue placeholder="All states" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All states</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="suspended">Suspended</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      {studios.isLoading ? (
        <p className="text-muted-foreground text-sm" role="status">Loading studios...</p>
      ) : (
        <div className="rounded-md border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Display Name</TableHead>
                <TableHead>Timezone</TableHead>
                <TableHead>State</TableHead>
                <TableHead>Beta</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                    {search || stateFilter !== "all"
                      ? "No studios match your filters."
                      : "No studios yet."}
                  </TableCell>
                </TableRow>
              ) : (
                filtered.map((studio) => (
                  <TableRow key={studio.id}>
                    <TableCell>
                      <Link
                        href={`/studios/${studio.id}`}
                        className="font-medium text-primary hover:underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring rounded-sm"
                      >
                        {studio.name}
                      </Link>
                    </TableCell>
                    <TableCell>{studio.display_name ?? "—"}</TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {studio.timezone}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          studio.state === "active"
                            ? "default"
                            : studio.state === "suspended"
                              ? "destructive"
                              : "secondary"
                        }
                      >
                        {studio.state}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {studio.beta_cohort ? (
                        <Badge variant="outline">Beta</Badge>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {new Date(studio.created_at).toLocaleDateString()}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
