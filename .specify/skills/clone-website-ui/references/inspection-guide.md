# Inspection Guide

What to capture when reverse-engineering a page via the `browser-utils` skill. Feeds `docs/research/BEHAVIORS.md`, `docs/research/PAGE_TOPOLOGY.md`, and every component spec.

## Behavior Catalog

Behaviors are invisible in a static screenshot but define how the page *feels*. Watch for these — illustrative, not exhaustive:
- Navbar that shrinks / changes background / gains a shadow after scrolling past a threshold
- Elements that animate into view on viewport entry (fade-up, slide-in, stagger delays)
- Sections that snap into place on scroll (`scroll-snap-type`)
- Parallax layers moving at different rates than the scroll
- Hover states that animate (transition duration & easing matter, not just the end state)
- Dropdowns, modals, accordions with enter/exit animations
- Scroll-driven progress indicators or opacity transitions
- Auto-playing carousels or cycling content
- Dark-to-light (or any theme) transitions between page sections
- **Tabbed/pill content that cycles** — buttons switching visible card sets with transitions
- **Scroll-driven tab/accordion switching** — sidebars whose active item auto-changes as content scrolls past (IntersectionObserver, NOT click handlers)
- **Smooth-scroll libraries** (Lenis, Locomotive Scroll) — check for `.lenis` / `.locomotive-scroll` classes or scroll-container wrappers

## Mandatory Interaction Sweep

A dedicated pass AFTER screenshots, BEFORE building anything. Save findings to `docs/research/BEHAVIORS.md`.

**Scroll sweep** — scroll slowly top to bottom; at each section pause and observe:
- Does the header change? Record the scroll position where it triggers.
- Do elements animate into view? Which ones, and the animation type.
- Does a sidebar / tab indicator auto-switch as you scroll? Record the mechanism.
- Are there scroll-snap points? Which containers.
- Is a smooth-scroll library active? (non-native scroll feel)

**Click sweep** — click every interactive-looking element (buttons, tabs, pills, links, cards):
- Record what happens: content change? modal opens? dropdown appears?
- For tabs/pills: click EACH and record the content per state.

**Hover sweep** — hover buttons, cards, links, images, nav items:
- Record what changes: color, scale, shadow, underline, opacity — and the transition timing.

**Responsive sweep** — test at 3 widths (Desktop 1440px / Tablet 768px / Mobile 390px):
- Note which sections change layout (column → stack, sidebar disappears) and the approximate breakpoint.

## Design Tokens Checklist
- **Colors** — background, text (primary/secondary/muted), accent, border, hover, error, success, warning
- **Typography** — family, sizes (h1–h6, body, caption, label), weights, line-heights, letter-spacing
- **Spacing** — padding/margin scale (4/8/12/16/24/32…)
- **Border radius** — buttons, cards, avatars, inputs
- **Shadows/elevation** — cards, dropdowns, modal overlay
- **Breakpoints** — where the layout shifts
- **Icons** — which library / custom SVGs / sizes
- **Buttons** — every variant (primary, secondary, ghost, icon-only, danger)
- **Inputs** — text, textarea, select, checkbox, toggle

## Component Inventory

For each distinct UI component document:
1. **Name** — what would you call it?
2. **Structure** — what elements / child components?
3. **Variants** — sizes, colors, states?
4. **States** — default, hover, active, disabled, loading, error, empty
5. **Responsive behavior** — how it changes per breakpoint
6. **Interactions** — click, hover, focus, keyboard
7. **Animations** — transitions, entrance/exit, micro-interactions

Common components to look for: navigation (top/side/bottom bar), cards/list items, buttons & links, forms & inputs, modals/dialogs, dropdowns/menus, tabs/segmented controls, avatars/badges, loading skeletons, toasts, tooltips/popovers.

## Layout Architecture
- **Grid system** — CSS Grid? Flexbox? Fixed widths?
- **Columns** — how many at each breakpoint?
- **Max-width** — main content area
- **Sticky elements** — header, sidebar, floating buttons
- **Z-index layers** — nav, modals, tooltips, overlays
- **Scroll behavior** — infinite scroll, pagination, virtual scrolling, snap

## Technical Stack Analysis (of the TARGET)
Understanding the source helps you extract accurately — you still rebuild in the chosen stack.
- **Framework** — check `__NEXT_DATA__`, `__NUXT__`, `ng-version`, React/Vue devtools markers
- **CSS approach** — utility classes (Tailwind), CSS Modules, styled-components, Emotion, vanilla
- **Fonts** — Google, self-hosted, system
- **Images** — CDN, lazy loading, `srcset`, WebP/AVIF
- **Animation library** — Framer Motion, GSAP, CSS transitions only, Lottie
