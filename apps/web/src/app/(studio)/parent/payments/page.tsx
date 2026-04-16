"use client";

import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

interface PaymentItem {
  id: string;
  amount: string;
  currency: string;
  status: string;
  method: string | null;
  memo: string | null;
  created_at: string;
}

interface PaymentsData {
  child_user_id: string;
  studio_id: string;
  total_pending: string;
  total_paid: string;
  total_refunded: string;
  payments: PaymentItem[];
}

function useChildPayments(childId: string) {
  return useQuery<PaymentsData>({
    queryKey: ["parent", "children", childId, "payments"],
    queryFn: () => apiFetch(`/parent/children/${childId}/payments`),
    enabled: !!childId,
  });
}

function statusVariant(status: string): "default" | "secondary" | "destructive" {
  switch (status) {
    case "paid":
      return "default";
    case "refunded":
      return "destructive";
    default:
      return "secondary";
  }
}

export default function ParentPaymentsPage() {
  const searchParams = useSearchParams();
  const childId = searchParams.get("child") ?? "";

  const payments = useChildPayments(childId);

  if (!childId) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-muted-foreground">
          Select a child from the dashboard to view their payment history.
        </p>
      </div>
    );
  }

  if (payments.isLoading) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-muted-foreground">Loading payments...</p>
      </div>
    );
  }

  if (payments.error) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-destructive" role="alert">
          Failed to load payments. You may not have permission to view this child&apos;s payments.
        </p>
      </div>
    );
  }

  const data = payments.data!;

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-8">
        <h1 className="font-display text-[40px] leading-[48px] font-semibold tracking-tight">
          Payment History
        </h1>
        <p className="text-muted-foreground mt-2">
          View-only payment summary and transaction history.
        </p>
      </div>

      {/* Balance Summary */}
      <div className="mb-8 grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Outstanding</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="font-display text-2xl font-bold tabular-nums">
              ${data.total_pending}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Paid</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="font-display text-2xl font-bold tabular-nums">
              ${data.total_paid}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Refunded</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="font-display text-2xl font-bold tabular-nums">
              ${data.total_refunded}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Transaction History */}
      <section aria-labelledby="history-heading">
        <h2 id="history-heading" className="mb-4 text-xl font-semibold">
          Transactions
        </h2>

        {data.payments.length === 0 ? (
          <p className="text-muted-foreground">No payment records yet.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Method</TableHead>
                <TableHead>Memo</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.payments.map((p) => (
                <TableRow key={p.id}>
                  <TableCell>
                    {new Date(p.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell className="tabular-nums">
                    ${p.amount} {p.currency}
                  </TableCell>
                  <TableCell>{p.method ?? "—"}</TableCell>
                  <TableCell>{p.memo ?? "—"}</TableCell>
                  <TableCell>
                    <Badge variant={statusVariant(p.status)}>
                      {p.status}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </section>
    </div>
  );
}
