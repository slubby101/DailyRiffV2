"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function HomePage() {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [studioName, setStudioName] = useState("");
  const [status, setStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("submitting");
    setErrorMessage("");

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/waitlist`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, name, studio_name: studioName }),
        },
      );

      if (!res.ok) {
        const body = await res.text();
        throw new Error(body || `Request failed (${res.status})`);
      }

      setStatus("success");
      setEmail("");
      setName("");
      setStudioName("");
    } catch (err) {
      setStatus("error");
      setErrorMessage(
        err instanceof Error ? err.message : "Something went wrong. Please try again.",
      );
    }
  }

  return (
    <>
      {/* Hero */}
      <section className="mx-auto max-w-6xl px-4 py-24 sm:px-6 sm:py-32 lg:px-8">
        <div className="max-w-2xl">
          <h1 className="font-display text-5xl font-bold tracking-tight sm:text-6xl">
            Practice made{" "}
            <span className="text-primary">personal</span>
          </h1>
          <p className="mt-6 text-lg leading-relaxed text-muted-foreground">
            DailyRiff connects music teachers, students, and parents in one
            place. Assign practice, track progress, and celebrate streaks &mdash;
            all without the paperwork.
          </p>
        </div>
      </section>

      {/* How it works */}
      <section
        aria-labelledby="how-it-works"
        className="border-t border-border bg-muted/30"
      >
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:px-8">
          <h2
            id="how-it-works"
            className="font-display text-3xl font-semibold tracking-tight"
          >
            How it works
          </h2>
          <ol className="mt-10 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {[
              {
                step: "1",
                title: "Teacher assigns",
                desc: "Create practice assignments with pieces, techniques, and due dates.",
              },
              {
                step: "2",
                title: "Student records",
                desc: "Students record 5\u201360 minutes of practice right from the app.",
              },
              {
                step: "3",
                title: "Auto-acknowledged",
                desc: "Recordings are automatically acknowledged \u2014 no manual check-ins needed.",
              },
              {
                step: "4",
                title: "Teacher reviews",
                desc: "Listen back, leave feedback, and track each student\u2019s progress over time.",
              },
            ].map(({ step, title, desc }) => (
              <li key={step} className="flex flex-col gap-3">
                <span className="font-display text-4xl font-bold text-primary/30">
                  {step}
                </span>
                <h3 className="text-lg font-semibold">{title}</h3>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {desc}
                </p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* For teachers */}
      <section
        aria-labelledby="for-teachers"
        className="border-t border-border"
      >
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:px-8">
          <h2
            id="for-teachers"
            className="font-display text-3xl font-semibold tracking-tight"
          >
            For teachers
          </h2>
          <ul className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {[
              "Create and manage your studio in minutes",
              "Invite students and parents with a single link",
              "Track lessons, attendance, and payment in one view",
              "Get notified when students submit recordings",
              "Leave detailed feedback on each practice session",
              "Share resources and sheet music with your studio",
            ].map((item) => (
              <li
                key={item}
                className="text-sm leading-relaxed text-muted-foreground"
              >
                <span className="mr-2 font-semibold text-foreground">&bull;</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* For parents & students */}
      <section
        aria-labelledby="for-families"
        className="border-t border-border bg-muted/30"
      >
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:px-8">
          <h2
            id="for-families"
            className="font-display text-3xl font-semibold tracking-tight"
          >
            For parents &amp; students
          </h2>
          <ul className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {[
              "See upcoming lessons and assignments at a glance",
              "Record practice sessions from any device",
              "Build practice streaks and track weekly minutes",
              "Message your teacher directly in the app",
              "Parents can monitor progress for multiple children",
              "Age-appropriate experience for students 13+",
            ].map((item) => (
              <li
                key={item}
                className="text-sm leading-relaxed text-muted-foreground"
              >
                <span className="mr-2 font-semibold text-foreground">&bull;</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Waitlist */}
      <section
        aria-labelledby="waitlist"
        className="border-t border-border"
      >
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:px-8">
          <div className="max-w-lg">
            <h2
              id="waitlist"
              className="font-display text-3xl font-semibold tracking-tight"
            >
              Join the waitlist
            </h2>
            <p className="mt-3 text-sm text-muted-foreground">
              We&apos;re launching with a small group of studios. Sign up to be
              among the first.
            </p>

            {status === "success" ? (
              <div
                role="status"
                className="mt-6 rounded-lg border border-primary/30 bg-primary/5 px-4 py-3 text-sm"
              >
                <p className="font-medium">You&apos;re on the list!</p>
                <p className="mt-1 text-muted-foreground">
                  We&apos;ll reach out when it&apos;s your turn.
                </p>
              </div>
            ) : (
              <form
                onSubmit={handleSubmit}
                className="mt-6 flex flex-col gap-4"
                aria-label="Join the waitlist"
              >
                <div>
                  <label htmlFor="waitlist-name" className="text-sm font-medium">
                    Your name
                  </label>
                  <Input
                    id="waitlist-name"
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Jane Doe"
                    className="mt-1"
                    autoComplete="name"
                  />
                </div>

                <div>
                  <label htmlFor="waitlist-email" className="text-sm font-medium">
                    Email address
                  </label>
                  <Input
                    id="waitlist-email"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="jane@example.com"
                    className="mt-1"
                    autoComplete="email"
                  />
                </div>

                <div>
                  <label htmlFor="waitlist-studio" className="text-sm font-medium">
                    Studio name
                  </label>
                  <Input
                    id="waitlist-studio"
                    type="text"
                    value={studioName}
                    onChange={(e) => setStudioName(e.target.value)}
                    placeholder="Mitchell Music Studio"
                    className="mt-1"
                    autoComplete="organization"
                  />
                </div>

                {status === "error" && (
                  <p role="alert" className="text-sm text-destructive">
                    {errorMessage}
                  </p>
                )}

                <Button
                  type="submit"
                  disabled={status === "submitting"}
                  className="mt-2 w-full sm:w-auto"
                >
                  {status === "submitting" ? "Submitting\u2026" : "Join waitlist"}
                </Button>
              </form>
            )}
          </div>
        </div>
      </section>
    </>
  );
}
