import { cn } from "@/lib/utils";

interface DashboardAlertBannerProps {
  variant?: "info" | "warning" | "error" | "success";
  children: React.ReactNode;
  className?: string;
}

const variantStyles = {
  info: "bg-chart-2/10 text-chart-2 border-chart-2/20",
  warning: "bg-chart-5/10 text-chart-5 border-chart-5/20",
  error: "bg-destructive/10 text-destructive border-destructive/20",
  success: "bg-chart-4/10 text-chart-4 border-chart-4/20",
} as const;

export function DashboardAlertBanner({
  variant = "info",
  children,
  className,
}: DashboardAlertBannerProps) {
  return (
    <div
      role="alert"
      className={cn(
        "rounded-lg border px-4 py-3 text-sm",
        variantStyles[variant],
        className
      )}
    >
      {children}
    </div>
  );
}
