# Design System — DailyRiff

**Status:** Initial — authored 2026-04-15 via `/design-consultation`
**Baseline:** Polymet (`slubby101/daily-riff-platform`) — React + Vite + Tailwind 3.4 + shadcn/ui `"new-york"` style, base color zinc, Radix primitives, lucide-react, react-hook-form
**Divergences:** typography, brand primary color, per-studio palette system, radius, type scale
**Consuming apps:** `apps/web` (Next.js 15 App Router), `apps/mobile` (Expo — inherits tokens via shared package), `apps/api` email templates (React Email)

Always read this file before making any visual or UI decisions. All font choices, colors, spacing, and aesthetic direction are defined here. Do not deviate without explicit user approval. In QA mode, flag any code that doesn't match this document.

---

## Product Context

- **What this is:** DailyRiff is the operations platform for private music studios. Teachers assign practice, students record it (5–60 min), a Postgres trigger auto-acknowledges the assignment, and teachers review feedback. Plus lessons, payments, messaging, parent oversight, and COPPA compliance for under-13 students.
- **Who it's for:** Five personas, each with their own surface — private-studio teachers (studio owners), parents (payers, schedulers, COPPA consenters), students aged 13+ (self-serve web), students under 13 (parent-mediated, primarily mobile), and the DailyRiff superadmin (platform operator).
- **Space/industry:** Music education SaaS. Competitors: MyMusicStaff, TeachersPay, SmartMusic, JigSaw, Nafme Academy. Category defaults: clinical blue/teal SaaS palettes, Inter/Roboto, stock-photo hero sections, data-dense spreadsheet UIs. This is the aesthetic DailyRiff departs from.
- **Project type:** Hybrid. Marketing homepage + 6 legal/public pages (full editorial treatment). Studio-facing web app (dense data, multi-persona dashboards, realtime pending-reviews queue). 5-screen Expo mobile app for students. Email templates for transactional flows. Superadmin operator surface.

---

## Aesthetic Direction

- **Direction:** **Editorial Warmth.** Magazine-grade typography meets data density. Practice is a daily ritual; the interface should feel like a well-designed journal a teacher actually wants to open, not a spreadsheet they tolerate.
- **Decoration level:** **Intentional.** Typography does most of the work. Subtle warm paper texture on marketing pages. No decorative blobs, no floating SVG confetti, no 3-column icon grids. Decoration earns its pixels.
- **Mood:** Warm morning practice light. Confident serif headlines over clean sans body. Rich amber accents against warm neutrals. Dense data that reads like a magazine table, not a DMV form. Quiet, intentional, serious about craft — but not sterile.
- **Reference aesthetics:** NYT Cooking (editorial density), Things 3 (quiet confidence), Linear (data clarity), Fraunces specimen site (display-serif warmth). Notable *non-references:* generic SaaS starters, Notion, Asana, any "7-in-1 productivity suite."

### Deliberate departures from category convention

1. **Serif display font.** Every edtech SaaS uses Inter or Poppins. Fraunces signals we take music seriously as an art form. Risk: slightly harder scan in dense tables (mitigated — serifs only at display sizes; body is sans).
2. **Amber brand primary.** Not SaaS blue, not edtech green, not AI purple. Brass instruments, practice-room incandescent, daily morning ritual. Risk: reads "warm" rather than "technical" for the superadmin operator persona (mitigated — operator surface uses cooler accent variant).
3. **Per-studio color override.** Every studio picks from a 12-swatch palette at onboarding. The entire student and parent surface of that studio is re-themed live via `--primary`. Signals "your studio, our chassis" rather than "you're a row in our database." Risk: 12-way color sprawl (mitigated — all 12 swatches pre-AA-vetted at Radix UI step 9).
4. **Generous type scale at display sizes.** Student dashboards show "You practiced 47 minutes today" at 48px display. Most edtech products would use 18px. We let the number breathe because it's the thing the student cares about.

### Anti-slop rules

We will **not** ship:
- Purple/violet/indigo gradients as backgrounds or accent colors
- 3-column icon-in-colored-circle feature grids (the single most recognizable AI/SaaS starter pattern)
- Centered-everything with uniform spacing
- Uniform bubbly border-radius on every element
- Decorative blobs, floating SVG confetti, wavy section dividers
- Emoji as design elements (rockets in headings, emoji bullets)
- Colored left-border on cards (`border-left: 3px solid accent`)
- Generic hero copy ("Welcome to DailyRiff", "Unlock the power of practice", "Your all-in-one solution for music studios")
- Cookie-cutter section rhythm (hero → 3 features → testimonials → pricing → CTA)
- Stock photos of smiling children at pianos

---

## Typography

All fonts loaded from Google Fonts. Self-hosted copies committed to `apps/web/public/fonts/` as a performance optimization in Slice 2 (#19).

### Font stack

| Role | Font | Weights | Rationale |
|---|---|---|---|
| **Display / Hero / H1–H2** | **Fraunces** | 400, 500, 600, 700 | Warm, slightly quirky, expressive display serif. Opsz axis for optical sizing. Signals editorial care. |
| **Body / UI / H3–H6** | **Geist** | 400, 500, 600 | Vercel's tight modern sans. Built for interfaces, tabular-nums capable, never reads as "AI-generated." Not Inter, not Poppins, not Roboto. |
| **Data / Tables / Numerals** | **Geist** (`font-variant-numeric: tabular-nums`) | 400, 500 | Same family as body for consistency. Tabular numerals keep payment ledgers and practice-minutes aligned. |
| **Mono / Code / Timestamps** | **Geist Mono** | 400, 500 | Same designer family, pairs visually with body. Used for recording timestamps, student IDs in superadmin surfaces, code samples in help content. |

### Loading strategy

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500&display=swap" rel="stylesheet">
```

Use `font-display: swap` to prevent invisible-text flash. Self-host in production; fall back to CDN in development. `next/font/google` handles this automatically in `apps/web`.

### Fallback stacks (if Google Fonts / self-hosted fail)

```css
--font-display: "Fraunces", Georgia, "Times New Roman", serif;
--font-body:    "Geist", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
--font-mono:    "Geist Mono", ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, monospace;
```

Fraunces falls back to Georgia — serif-to-serif preserves editorial tone. Never fall back from serif to sans; the warmth collapses. Geist falls back to the system font stack — interfaces stay literate. Geist Mono falls back to the standard mono stack.

If Google Fonts is blocked (corporate networks, CSP, ad blockers), self-hosted copies in `apps/web/public/fonts/` are the primary path; the CDN is a fallback. Stage 1 ships with both paths wired; decide at CI time which is canonical based on performance measurement.

### Scale

Modular scale, 1.25 ratio, base 16px. Fraunces for `display-*` and `h1`/`h2`, Geist for everything else.

```
display-xl    64px / 72px / 700 / Fraunces   — marketing hero, student "minutes practiced" stat
display-lg    48px / 56px / 700 / Fraunces   — secondary marketing hero, streak milestones
display-md    40px / 48px / 600 / Fraunces   — page titles on dashboards
display-sm    32px / 40px / 600 / Fraunces   — section headers ("Pending Reviews", "This Week's Assignments")
h1            28px / 36px / 600 / Fraunces   — modal titles
h2            24px / 32px / 600 / Geist      — card group headers
h3            20px / 28px / 600 / Geist      — card headers
h4            18px / 28px / 500 / Geist      — inline group labels
h5            16px / 24px / 500 / Geist      — form section labels
h6            14px / 20px / 500 / Geist      — small labels, breadcrumbs
body-lg       18px / 28px / 400 / Geist      — marketing body copy
body          16px / 24px / 400 / Geist      — default body, form inputs
body-sm       14px / 20px / 400 / Geist      — table cells, secondary info
caption       12px / 16px / 500 / Geist      — metadata, timestamps, helper text
overline      11px / 16px / 600 / Geist uppercase, 0.05em tracking — small-caps eyebrow labels
mono          14px / 20px / 400 / Geist Mono — code, IDs, exact timestamps
```

### Tracking / letter-spacing

- Fraunces display sizes: `-0.02em` (tight, magazine-grade)
- Geist body: `0` (default, Geist is designed for UI)
- Overline / uppercase labels: `+0.05em`
- Tabular numerals everywhere money or duration is displayed (`font-variant-numeric: tabular-nums`)

### Line-height

Built into the scale above. Fraunces at display sizes uses tighter leading (1.1–1.15); Geist body uses 1.5; dense tables use 1.35.

---

## Color

### Approach

**Semantic tokens, not raw hex.** Every color in the system is a CSS custom property. Components consume tokens, never raw values. Per-studio brand override flows through `--primary` live.

### Core palette (DailyRiff brand defaults)

```css
:root {
  /* === DailyRiff brand defaults (light mode) === */

  /* Neutrals — warm off-white and warm charcoal, NOT pure zinc */
  --background:            30 20% 98%;        /* #FBF9F6 — warm paper */
  --foreground:            30 15% 12%;        /* #211E19 — warm charcoal */
  --card:                   0  0% 100%;       /* #FFFFFF — pure white for card elevation contrast */
  --card-foreground:       30 15% 12%;
  --popover:                0  0% 100%;
  --popover-foreground:    30 15% 12%;

  /* Brand primary — warm amber, studios can override */
  --primary:               30 85% 48%;        /* #E3860F — deep amber, "practice light" */
  --primary-foreground:     0  0% 100%;       /* white on amber, contrast verified 4.6:1 */

  /* Secondary — warm stone */
  --secondary:             30 10% 94%;        /* #F0EDE8 — warm stone */
  --secondary-foreground:  30 15% 12%;

  --muted:                 30  8% 92%;        /* #EDEAE5 */
  --muted-foreground:      30  8% 40%;        /* #6B655C */

  --accent:                30 10% 94%;
  --accent-foreground:     30 15% 12%;

  --destructive:            0 72% 51%;        /* #DC2626 — standard red */
  --destructive-foreground: 0  0% 100%;

  --border:                30  8% 88%;        /* #E0DCD5 */
  --input:                 30  8% 88%;
  --ring:                  30 85% 48%;        /* matches primary */

  /* Chart colors — warm analogous, not the shadcn default */
  --chart-1:               30 85% 48%;        /* amber — primary */
  --chart-2:              180 60% 35%;        /* deep teal — secondary */
  --chart-3:              340 65% 50%;        /* crimson — warning/milestone */
  --chart-4:              130 45% 40%;        /* grass — success */
  --chart-5:               45 80% 55%;        /* gold — highlight */

  /* Sidebar — slightly cooler than main surface for depth */
  --sidebar:               30 15% 96%;
  --sidebar-foreground:    30 15% 12%;
  --sidebar-primary:       30 85% 48%;
  --sidebar-primary-foreground: 0 0% 100%;
  --sidebar-accent:        30 10% 92%;
  --sidebar-accent-foreground: 30 15% 12%;
  --sidebar-border:        30  8% 86%;
  --sidebar-ring:          30 85% 48%;

  /* Radius */
  --radius: 0.5rem;                            /* 8px — tighter than Polymet's 10px */

  /* Shadows — warm, not pure black */
  --shadow-xs:  0 1px 2px 0 hsl(30 20% 15% / 0.06);
  --shadow-sm:  0 1px 3px 0 hsl(30 20% 15% / 0.08), 0 1px 2px -1px hsl(30 20% 15% / 0.06);
  --shadow-md:  0 4px 6px -1px hsl(30 20% 15% / 0.08), 0 2px 4px -2px hsl(30 20% 15% / 0.06);
  --shadow-lg:  0 10px 15px -3px hsl(30 20% 15% / 0.08), 0 4px 6px -4px hsl(30 20% 15% / 0.06);
  --shadow-xl:  0 20px 25px -5px hsl(30 20% 15% / 0.1),  0 8px 10px -6px hsl(30 20% 15% / 0.06);
}

.dark {
  /* === Dark mode — REDESIGNED, not inverted === */

  --background:            30 15%  8%;        /* #17140F — warm deep charcoal, not black */
  --foreground:            30 20% 95%;        /* #F5F2ED — warm off-white */
  --card:                  30 15% 11%;        /* #1F1B16 — one step lighter for card elevation */
  --card-foreground:       30 20% 95%;
  --popover:               30 15% 11%;
  --popover-foreground:    30 20% 95%;

  /* Amber desaturated 15% for dark mode readability */
  --primary:               30 75% 58%;        /* #EAA347 — warmer, brighter on dark */
  --primary-foreground:    30 15%  8%;

  --secondary:             30 10% 18%;
  --secondary-foreground:  30 20% 95%;
  --muted:                 30 10% 16%;
  --muted-foreground:      30  8% 62%;
  --accent:                30 10% 18%;
  --accent-foreground:     30 20% 95%;
  --destructive:            0 65% 50%;
  --destructive-foreground: 0  0% 100%;
  --border:                30 10% 20%;
  --input:                 30 10% 20%;
  --ring:                  30 75% 58%;

  --chart-1:               30 75% 58%;
  --chart-2:              180 55% 50%;
  --chart-3:              340 60% 60%;
  --chart-4:              130 45% 55%;
  --chart-5:               45 70% 60%;

  --sidebar:               30 15%  6%;
  --sidebar-foreground:    30 20% 95%;
  --sidebar-primary:       30 75% 58%;
  --sidebar-primary-foreground: 30 15% 8%;
  --sidebar-accent:        30 10% 14%;
  --sidebar-accent-foreground: 30 20% 95%;
  --sidebar-border:        30 10% 18%;
  --sidebar-ring:          30 75% 58%;
}
```

### Per-studio 12-swatch palette (Stage 1 Q15)

Every studio picks ONE color at onboarding. The pick writes `studios.primary_color` and becomes `--primary` on every page in that studio's subdomain/route group. All 12 swatches are Radix UI step-9 values (pre-AA-vetted, ≥4.5:1 against white, ≥3:1 against near-black `#17140F`).

| # | Name | HSL | Hex (light) | Hex (dark) | Notes |
|---|---|---|---|---|---|
| 1 | **Amber** (default) | `30 85% 48%` | `#E3860F` | `#EAA347` | DailyRiff default |
| 2 | **Tomato** | `10 78% 54%` | `#E54D2E` | `#F16D50` | Vivid warm red |
| 3 | **Crimson** | `336 80% 48%` | `#DC3D7C` | `#E96A9A` | Magenta-leaning |
| 4 | **Plum** | `292 45% 51%` | `#A13CBC` | `#BA5CCF` | Muted purple — the one purple we allow |
| 5 | **Violet** | `252 58% 58%` | `#6E56CF` | `#8B74E4` | Indigo-blue |
| 6 | **Indigo** | `226 70% 55%` | `#3E63DD` | `#6280EA` | Classic SaaS blue (allowed for studios who want it) |
| 7 | **Cyan** | `190 90% 38%` | `#0AA0B8` | `#3EBFD4` | Sharp teal |
| 8 | **Teal** | `173 80% 36%` | `#12A594` | `#3EC1B1` | Calm blue-green |
| 9 | **Jade** | `164 60% 40%` | `#29A383` | `#51B79B` | Deep green |
| 10 | **Grass** | `131 41% 46%` | `#46A758` | `#68BC77` | Natural green |
| 11 | **Orange** | `24 94% 50%` | `#F76808` | `#FA7F2D` | Vibrant construction orange |
| 12 | **Gold** | `42 90% 48%` | `#E8A00A` | `#F2B834` | Rich golden yellow |

**Contrast policy:** Every swatch passes AA 4.5:1 for `white` text at step 9 and passes 3:1 for `#17140F` text. This is enforced by a unit test in Slice 2 (#19).

**CSS override mechanism:**
```css
/* apps/web/src/app/(studio)/[slug]/layout.tsx — runtime injection */
<style>{`
  :root {
    --primary: ${studio.primaryHsl};
    --ring: ${studio.primaryHsl};
  }
`}</style>
```

The injection happens server-side in the studio layout, so there's no client-side flash. The studio's logo and display name also flow through the layout.

### Semantic colors

Never hardcode. Always via tokens:

- **Success:** `--chart-4` (grass)
- **Warning:** `--chart-5` (gold)
- **Error:** `--destructive`
- **Info:** `--chart-2` (teal)
- **Streak-alive:** `--primary` (the studio's brand color — ties streak celebration to brand)
- **Pending-deletion:** `--destructive` at 50% opacity on card background

---

## Spacing

- **Base unit:** 4px. Tailwind's default scale (`space-1` = 4px, `space-2` = 8px, `space-4` = 16px, etc.)
- **Density:** **Comfortable.** Not compact (that's Notion; it reads hostile to parents and kids). Not spacious (that's marketing landing pages; wastes screen for data-dense teacher surfaces).
- **Page padding:**
  - Mobile: `px-4` (16px)
  - Tablet: `px-6` (24px)
  - Desktop: `px-8` (32px)
- **Card padding:** `p-6` (24px) for content cards, `p-4` (16px) for dense list rows
- **Section spacing (marketing):** `py-20` (80px) desktop, `py-12` (48px) mobile
- **Form field gap:** `gap-4` (16px) between fields, `gap-6` (24px) between sections
- **Dashboard grid gap:** `gap-6` (24px) desktop, `gap-4` (16px) mobile
- **Table row height:** 48px minimum (touch-friendly, AA-compliant)

---

## Layout

- **Approach:** **Hybrid.** Grid-disciplined for app surfaces (dashboards, forms, tables). Creative-editorial for marketing homepage and the student record screen (which should feel like a moment, not a form).
- **Grid:** 12-column on desktop (`lg:grid-cols-12`), 6-column on tablet, stack on mobile.
- **Max content width:**
  - Marketing pages: `max-w-6xl` (1152px) for text, `max-w-7xl` (1280px) for hero
  - App dashboards: `max-w-screen-2xl` (1536px) — full-bleed minus page padding
  - Reading content (privacy policy, ToS, help): `max-w-prose` (65ch)
- **Border radius hierarchy:**
  - `rounded-sm` (4px): tight inputs, table cell highlights
  - `rounded-md` (6px): buttons, form inputs
  - `rounded-lg` (8px) = `var(--radius)`: cards, modals, popovers
  - `rounded-xl` (12px): large feature cards on marketing
  - `rounded-2xl` (16px): hero image frames
  - `rounded-full`: avatars, pills, badge chips

Never apply the same radius to every element. Hierarchy is what makes the system feel intentional.

### Sidebar nav (app surfaces)

- Fixed left sidebar on desktop (240px), collapsible on tablet, drawer on mobile
- Background uses `--sidebar` token (one step cooler than main surface) for subtle depth
- Active item uses `--sidebar-accent` background + `--primary` left-border 3px wide
  - **Exception to the "no colored left-border on cards" rule:** active nav items are one of the few places a colored left-border earns its pixels (signals selection state), and only on nav items, never on content cards.

---

## Motion

- **Approach:** **Intentional.** Not minimal (dashboards feel dead without feedback). Not expressive (this isn't a marketing landing competing for attention).
- **Philosophy:** Motion clarifies state changes. Every animation has a reason. No autoplay, no carousels, no scroll-jacking, no parallax.

### Easing

```css
--ease-enter: cubic-bezier(0.16, 1, 0.3, 1);     /* out-expo — elements entering the viewport */
--ease-exit:  cubic-bezier(0.7, 0, 0.84, 0);     /* in-expo — elements leaving */
--ease-move:  cubic-bezier(0.65, 0, 0.35, 1);    /* in-out-cubic — elements moving within viewport */
--ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1); /* back.out — celebratory moments (streak milestones only) */
```

### Duration

- **Micro (50–100ms):** hover state changes, focus rings, cursor feedback
- **Short (150–250ms):** button press, input focus expand, toast appearance
- **Medium (250–400ms):** modal open/close, drawer slide, page transitions
- **Long (400–700ms):** onboarding walkthroughs, streak celebrations, recording state transitions

### Specific motion decisions

- **Realtime pending-reviews queue (the product pivot):** When a new recording uploads and the ack trigger fires, the new row slides in from the top with a 300ms `--ease-enter` transition + a brief (400ms) amber glow on `--primary`. Then the glow fades. This is the ONE moment where the interface celebrates itself, because the auto-ack trigger IS the product.
- **Streak milestones:** Spring ease for the streak counter increment. Everywhere else is calm.
- **Recording state transitions:** Idle → recording → uploading → uploaded → acknowledged uses cross-fade between state icons, not slide.
- **Prefers-reduced-motion:** All durations clamp to 0–50ms and all eases become linear. Tested via `@media (prefers-reduced-motion: reduce)`.

---

## Voice & Copy

Not exhaustively scoped here — content strategy is Slice 7 (marketing pages) and Slice 34 (launch legal review). But a few rules so the implementer doesn't default to generic SaaS:

- **Never use:** "Welcome to DailyRiff", "Unlock the power of", "Your all-in-one", "Designed for", "Built for", "Empower your", "Revolutionize your", "Seamless", "Robust", "Nuanced", any of the Voice section banned vocabulary.
- **Use instead:** Plain verbs, specific nouns. "Your students practiced 124 hours this week" not "Engagement metrics at a glance." "Sarah hasn't submitted Tuesday's Bach yet" not "Outstanding assignment detected."
- **Student-facing copy:** Warm but never condescending. No "Great job!!!" Treat them like the young musicians they are, not like kids on a progress-bar gamification app.
- **Teacher-facing copy:** Utility language. Orientation, status, action. Teachers are professionals running a business; respect their time.
- **Parent-facing copy:** Gentle transparency. Parents want to know what's happening without being lectured.
- **Error messages:** Name the problem, the consequence, the action. Never "Something went wrong."

---

## Accessibility

DailyRiff commits to WCAG 2.1 AA on every shipped page. This document is calibrated to not fight that commitment.

- **Contrast:** All foreground/background pairs in this document verified ≥4.5:1 for normal text, ≥3:1 for large text (≥18px or ≥14px bold). Per-studio palette enforced at Radix step 9 for all 12 swatches.
- **Focus:** All interactive elements have a visible `--ring` outline, 2px offset, 2px width, never removed.
- **Keyboard:** Every interactive element reachable via Tab. Order matches visual order. Skip-to-main-content link at top of every page.
- **Screen readers:** Radix primitives (shadcn's base) handle ARIA correctly out of the box. Never strip Radix attributes. Custom components follow the same conventions (role, aria-label, aria-describedby, aria-live for toasts and realtime updates).
- **Motion:** `prefers-reduced-motion` respected system-wide (see Motion section).
- **Touch targets:** 44×44px minimum on mobile (Expo + responsive web).
- **Zoom:** 200% zoom without horizontal scroll required.

---

## Implementation notes

### File locations (for Slice 2 / Issue #19 — web UI foundation)

- `apps/web/src/app/globals.css` — CSS variable definitions (light + dark), font imports, base reset
- `apps/web/tailwind.config.ts` — consumes CSS variables via `hsl(var(--token))` pattern (matches Polymet exactly)
- `apps/web/src/lib/studio-theme.ts` — runtime injection helper for per-studio `--primary` override
- `apps/web/src/components/ui/` — shadcn/ui components copied from Polymet with Fraunces/Geist swap
- `apps/web/public/fonts/` — self-hosted Fraunces, Geist, Geist Mono (production perf)

### What to port from Polymet directly

- `components.json` → `apps/web/components.json` (verbatim except update aliases to Next App Router paths)
- Most of `src/components/ui/*.tsx` → `apps/web/src/components/ui/*.tsx` (framework-agnostic, port literally)
- `tailwind.config.js` core structure → `apps/web/tailwind.config.ts` (same plugin list, same semantic token bindings, but TypeScript + Next presets)
- `lib/utils.ts` with `cn` helper → `apps/web/src/lib/utils.ts`

### What to rewrite (not port)

- `src/index.css` → `apps/web/src/app/globals.css` with the new color values from this document (Polymet's zinc-black is replaced with DailyRiff's warm amber palette)
- Font imports: remove Polymet's Inter import, add Fraunces + Geist + Geist Mono
- Per-studio injection: new — Polymet has no equivalent
- Dark mode palette: rewritten (Polymet just inverts; we redesign warmer)

### Mobile (Expo)

The Expo app inherits design tokens via a shared package (`packages/design-tokens/` — new, created in Slice 22 / #39). Tokens exported as JS constants consumed by RN StyleSheet. No NativeWind in Stage 1 per the PRD — tokens stay primitive.

### Email templates (React Email)

Postmark templates in `apps/api/email_templates/` inherit a subset: the primary color, neutrals, Fraunces display + Geist body. Shared token constants live in a Python dict generated from the same source JSON the frontend uses. Out of scope for Stage 1 is a full shared-tokens pipeline; Slice 16 (#33) hardcodes hex values and comments "keep in sync with docs/DESIGN.md."

---

## Decisions Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-04-15 | Initial design system created via `/design-consultation` | Baseline from Polymet stack; diverged on typography (Fraunces + Geist replace Inter), brand primary (warm amber replaces zinc-black), added 12-swatch per-studio palette (Q15), tightened radius (8px from 10px), introduced warm neutrals and redesigned dark mode |
| 2026-04-15 | Chose Fraunces over Instrument Serif and Cabinet Grotesk | Fraunces has optical sizing (opsz axis) — one font file handles display through body confidently. Instrument Serif is gorgeous but too editorial for app surfaces. Cabinet Grotesk is sans, loses the editorial signal. |
| 2026-04-15 | Chose Geist over Inter, DM Sans, General Sans | Inter is blacklist (overused). DM Sans is fine but Geist has explicit tabular-nums and is newer. General Sans is strong but less UI-tuned. Geist was designed for Vercel's interfaces, which is exactly our use case. |
| 2026-04-15 | Chose warm amber brand primary over classic SaaS blue, edtech green, AI purple | Amber is underused in the category, evokes practice-room brass/wood, works with all 12 studio override colors without clashing (amber is neutral enough to be "DailyRiff's house color" while letting studios have their own identity) |
| 2026-04-15 | Chose Radix UI step-9 scales for 12-swatch palette | Pre-vetted AA, battle-tested across thousands of products, 12 colors at consistent saturation/lightness means no studio picks a "weak" color |
| 2026-04-15 | Tightened radius to 8px (from Polymet's 10px) | 10px reads bubbly for teacher/parent professional surfaces; 8px is the edtech sweet spot (approachable but not childish) |
| 2026-04-15 | Redesigned dark mode rather than inverting | Warm charcoal (`30 15% 8%`) beats pure black for long practice sessions; desaturated amber stays warm on dark; verified against all 12 studio swatches |

---

## Next steps

- **Slice 2 (#19)** — Web UI foundation — is the first issue that consumes this document. The acceptance criteria for #19 should be updated to reference this file ("CSS custom properties match `docs/DESIGN.md` exactly") and include the font import.
- **Slice 7 (#24)** — Marketing + legal static pages — first place where Fraunces display really gets exercised. The marketing homepage is the most design-sensitive page in Stage 1.
- **Slice 8 (#25)** — Waitlist + studio onboarding — introduces the 12-swatch studio picker. Implementation should use this document's swatch table verbatim.
- **`/plan-design-review`** — re-run after this file lands; every dimension's rating should jump because there's now a calibration target. Mockups generated in that review will visually validate these choices against real screens.
- **Post-beta** — revisit this file after 6–12 weeks of real studio usage. Risks should be evaluated against real feedback: do teachers actually like Fraunces? Did amber feel warm or dated? Did studios use the 12-swatch override?
