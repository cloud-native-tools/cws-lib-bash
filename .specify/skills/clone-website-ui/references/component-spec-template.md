# Component Spec Template

Every section (or sub-component, when split) gets one spec file at `docs/research/components/<component-name>.spec.md` **before** any builder is dispatched. Fill every section; write "N/A" only after genuinely confirming it applies. The builder receives this file's contents inline.

```markdown
# <ComponentName> Specification

## Overview
- **Target file:** `<path in the chosen stack's idiom, e.g. src/components/HeroSection.tsx>`
- **Screenshot:** `docs/design-references/<screenshot-name>.png`
- **Interaction model:** <static | click-driven | scroll-driven | time-driven>

## DOM Structure
<Element hierarchy — what contains what>

## Computed Styles (exact values from getComputedStyle)

### Container
- display: ...
- padding: ...
- maxWidth: ...
- (every relevant property, exact values)

### <Child element 1>
- fontSize: ...
- color: ...
- (every relevant property)

### <Child element N>
...

## States & Behaviors

### <Behavior name, e.g. "Scroll-triggered floating mode">
- **Trigger:** <exact mechanism — scroll position 50px, IntersectionObserver rootMargin "-30% 0px", click on .tab-button, hover>
- **State A (before):** maxWidth: 100vw, boxShadow: none, borderRadius: 0
- **State B (after):** maxWidth: 1200px, boxShadow: 0 4px 20px rgba(0,0,0,0.1), borderRadius: 16px
- **Transition:** transition: all 0.3s ease
- **Implementation approach:** <CSS transition + scroll listener | IntersectionObserver | CSS animation-timeline | etc.>

### Hover states
- **<Element>:** <property>: <before> → <after>, transition: <value>

## Per-State Content (if applicable)

### State: "Featured"
- Title: "..."
- Subtitle: "..."
- Cards: [{ title, description, image, link }, ...]

### State: "Productivity"
- Cards: [...]

## Assets
- Background image: `<static-dir>/images/<file>.webp`
- Overlay image: `<static-dir>/images/<file>.png`
- Icons used: <ArrowIcon>, <SearchIcon>

## Text Content (verbatim)
<All text content, copy-pasted from the live site>

## Responsive Behavior
- **Desktop (1440px):** <layout description>
- **Tablet (768px):** <what changes — e.g. "maintains 2-column, gap reduces to 16px">
- **Mobile (390px):** <what changes — e.g. "stacks to single column, images full-width">
- **Breakpoint:** layout switches at ~<N>px
```

## Filling Notes
- **States & Behaviors** — think twice before marking N/A. Even a static footer usually has link hover states.
- **Computed Styles** — paste exact values from the CSS walker (`extraction-scripts.md` §2), not estimates.
- **Assets** — reference the *local downloaded* paths, never remote URLs.
- **Complexity check** — if the filled spec exceeds ~150 lines, the section is too big for one builder; split it and write one spec per sub-component.
