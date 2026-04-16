import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "About | DailyRiff",
  description:
    "DailyRiff connects music teachers, students, and parents in one place.",
};

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-prose px-4 py-16 sm:px-6 lg:px-8">
      <h1 className="font-display text-4xl font-bold tracking-tight">
        About DailyRiff
      </h1>

      <div className="mt-8 space-y-6 text-base leading-relaxed text-muted-foreground">
        <p>
          DailyRiff is a practice-management platform built for private music
          studios. We connect teachers, students, and parents so that daily
          practice becomes visible, accountable, and rewarding.
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          Why we exist
        </h2>
        <p>
          Most music students practice alone. Teachers assign work in lessons,
          but have no window into what happens at home between sessions.
          Parents want to help, but often lack the musical background to know
          whether practice is on track. DailyRiff closes that loop.
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          How it works
        </h2>
        <p>
          Teachers create assignments with specific pieces and techniques.
          Students record their practice sessions directly in the app &mdash;
          anywhere from 5 to 60 minutes. Recordings are automatically
          acknowledged, and teachers can listen back, leave feedback, and track
          progress over time. Parents get visibility into their children&apos;s
          practice habits without needing to be in the room.
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          Our approach
        </h2>
        <p>
          We&apos;re starting small &mdash; a controlled beta with a handful of
          studios &mdash; because we believe great software comes from working
          closely with the people who use it. Every feature is shaped by real
          teachers running real studios.
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          Privacy first
        </h2>
        <p>
          Many of our users are children. We take that responsibility seriously.
          DailyRiff is designed with COPPA compliance, strong data isolation
          between studios, and transparent data practices from day one. Read our{" "}
          <a
            href="/legal/privacy-policy"
            className="text-primary underline underline-offset-2 hover:text-primary/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            Privacy Policy
          </a>{" "}
          for details.
        </p>
      </div>
    </div>
  );
}
