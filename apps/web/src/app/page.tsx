import { ThemeToggle } from "@/components/theme-toggle";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <h1 className="font-display text-4xl font-bold tracking-tight">
        DailyRiff
      </h1>
      <p className="text-muted-foreground">Your daily music companion</p>
      <ThemeToggle />
    </main>
  );
}
