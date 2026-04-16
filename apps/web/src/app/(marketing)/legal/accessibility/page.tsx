import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Accessibility | DailyRiff",
  description: "DailyRiff accessibility statement and commitment.",
};

function DraftBanner() {
  return (
    <div
      role="alert"
      className="rounded-lg border border-primary/30 bg-primary/5 px-4 py-3 text-sm"
    >
      <p className="font-semibold">DRAFT &mdash; legal review pending</p>
      <p className="mt-1 text-muted-foreground">
        This document is a working draft and has not yet been reviewed by legal
        counsel. Final copy will replace this before public launch.
      </p>
    </div>
  );
}

export default function AccessibilityPage() {
  return (
    <div className="mx-auto max-w-prose px-4 py-16 sm:px-6 lg:px-8">
      <h1 className="font-display text-4xl font-bold tracking-tight">
        Accessibility Statement
      </h1>
      <p className="mt-2 text-sm text-muted-foreground">
        Last updated: April 2026
      </p>

      <div className="mt-6">
        <DraftBanner />
      </div>

      <div className="mt-8 space-y-6 text-base leading-relaxed text-muted-foreground">
        <h2 className="font-display text-2xl font-semibold text-foreground">
          Our commitment
        </h2>
        <p>
          DailyRiff is committed to making our platform accessible to all users,
          including people with disabilities. We target conformance with the Web
          Content Accessibility Guidelines (WCAG) 2.1 at the AA level.
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          What we do
        </h2>
        <ul className="list-disc space-y-2 pl-6">
          <li>
            All interactive elements have visible focus indicators and can be
            operated with a keyboard alone.
          </li>
          <li>
            Color contrast meets or exceeds 4.5:1 for normal text and 3:1 for
            large text across both light and dark themes.
          </li>
          <li>
            We use semantic HTML and ARIA attributes so screen readers can
            navigate the interface.
          </li>
          <li>
            Touch targets are at least 44&times;44 pixels on mobile devices.
          </li>
          <li>
            The interface remains usable at 200% browser zoom without horizontal
            scrolling.
          </li>
          <li>
            Animations respect the <code className="font-mono text-xs">prefers-reduced-motion</code>{" "}
            system setting.
          </li>
          <li>
            A &ldquo;skip to main content&rdquo; link is available at the top of
            every page.
          </li>
        </ul>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          Testing
        </h2>
        <p>
          We test with axe-core automated scans on every page, Lighthouse
          accessibility audits (targeting a score of 95+), keyboard-only
          navigation, and screen reader testing with VoiceOver and NVDA.
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          Known limitations
        </h2>
        <p>
          As a platform in active development, some newer features may not yet
          meet our full accessibility standards. We are continuously working to
          identify and resolve any gaps.
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          Feedback
        </h2>
        <p>
          If you encounter any accessibility barriers, please contact us at{" "}
          <a
            href="mailto:privacy@dailyriff.com"
            className="text-primary underline underline-offset-2 hover:text-primary/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            privacy@dailyriff.com
          </a>
          . We take all accessibility feedback seriously and aim to respond
          within 5 business days.
        </p>
      </div>
    </div>
  );
}
