import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Contact | DailyRiff",
  description: "Get in touch with the DailyRiff team.",
};

export default function ContactPage() {
  return (
    <div className="mx-auto max-w-prose px-4 py-16 sm:px-6 lg:px-8">
      <h1 className="font-display text-4xl font-bold tracking-tight">
        Contact us
      </h1>

      <div className="mt-8 space-y-6 text-base leading-relaxed text-muted-foreground">
        <p>
          We&apos;d love to hear from you. Whether you&apos;re a music teacher
          interested in the beta, a parent with a question, or just curious about
          DailyRiff &mdash; reach out anytime.
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          General inquiries
        </h2>
        <p>
          Email us at{" "}
          <a
            href="mailto:hello@dailyriff.com"
            className="text-primary underline underline-offset-2 hover:text-primary/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            hello@dailyriff.com
          </a>
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          Privacy &amp; data requests
        </h2>
        <p>
          For privacy-related questions, data access requests, or COPPA
          inquiries, contact our privacy team at{" "}
          <a
            href="mailto:privacy@dailyriff.com"
            className="text-primary underline underline-offset-2 hover:text-primary/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            privacy@dailyriff.com
          </a>
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          Beta program
        </h2>
        <p>
          Interested in bringing DailyRiff to your studio? We&apos;re currently
          accepting applications for our controlled beta.{" "}
          <a
            href="/#waitlist"
            className="text-primary underline underline-offset-2 hover:text-primary/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            Join the waitlist
          </a>{" "}
          and we&apos;ll be in touch.
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          Accessibility
        </h2>
        <p>
          If you encounter any accessibility barriers on our site, please let us
          know at{" "}
          <a
            href="mailto:privacy@dailyriff.com"
            className="text-primary underline underline-offset-2 hover:text-primary/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            privacy@dailyriff.com
          </a>
          . We are committed to making DailyRiff usable for everyone.
        </p>
      </div>
    </div>
  );
}
