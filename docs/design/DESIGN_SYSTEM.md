# sb dashboard — Design System

## Intent

The system is dark-first, light-mode compatible, dense by default, and tuned for a macOS desktop utility. It follows the user constraint to stay Linear-like: muted grays, one accent color, sharp hierarchy, minimal decoration, high signal density.

## Color tokens

### Core accent

Chosen accent: **sb violet** `#5E6AD2`

Reason:

- close to the requested Linear-purple family
- strong enough for focus and active state without overpowering data-heavy screens
- pairs cleanly with blue-tinted dark neutrals already requested

### Dark theme palette

| Token | Hex | Use |
|---|---:|---|
| `--bg-app` | `#0C111B` | app background |
| `--bg-panel` | `#121826` | cards, sidebars, flyouts |
| `--bg-elevated` | `#171F30` | hover cards, active list rows |
| `--border-subtle` | `#253047` | separators, table borders |
| `--border-strong` | `#33415C` | focused containers, selected panels |
| `--text-primary` | `#F5F7FB` | primary text |
| `--text-secondary` | `#A7B0C0` | labels, metadata |
| `--text-muted` | `#7C879A` | tertiary text |
| `--accent` | `#5E6AD2` | active nav, focus, buttons |
| `--accent-soft` | `#2A326C` | accent fills, pills |
| `--success` | `#3FB68B` | healthy sync, approved state |
| `--warn` | `#D9A441` | degraded adapter, caution |
| `--danger` | `#E06D6D` | rejection, destructive actions |
| `--info` | `#5DA8FF` | secondary emphasis, info states |

### Neutral gray scale

Five-step required scale:

| Token | Hex | Typical use |
|---|---:|---|
| `--neutral-950` | `#0C111B` | global background |
| `--neutral-900` | `#121826` | panels |
| `--neutral-800` | `#253047` | borders |
| `--neutral-700` | `#33415C` | hovered borders, dividers |
| `--neutral-500` | `#7C879A` | muted copy |

### Light theme palette

| Token | Hex | Use |
|---|---:|---|
| `--bg-app-light` | `#F7F9FC` | app background |
| `--bg-panel-light` | `#FFFFFF` | cards |
| `--bg-elevated-light` | `#EEF2F8` | hover rows |
| `--border-subtle-light` | `#D9E0EB` | separators |
| `--text-primary-light` | `#101828` | primary text |
| `--text-secondary-light` | `#475467` | metadata |

### Usage examples

```css
.app-shell { background: var(--bg-app); color: var(--text-primary); }
.sidebar { background: var(--bg-panel); border-right: 1px solid var(--border-subtle); }
.nav-item--active { background: color-mix(in srgb, var(--accent) 14%, transparent); color: var(--text-primary); }
.status-dot--ok { background: var(--success); }
.danger-button { color: var(--danger); }
```

## Typography

### Font stack

Use the required system stack with Inter Variable first:

```css
font-family: "Inter Variable", "Inter", "SF Pro Display", "SF Pro Text", -apple-system, BlinkMacSystemFont, sans-serif;
```

### Type ramp

| Token | Size | Line height | Weight | Use |
|---|---:|---:|---:|---|
| `--text-12` | 12px | 16px | 500 | badges, metadata |
| `--text-13` | 13px | 18px | 500 | dense UI labels |
| `--text-14` | 14px | 20px | 500 | default body |
| `--text-16` | 16px | 24px | 600 | panel headers |
| `--text-20` | 20px | 28px | 600 | page headers |
| `--text-24` | 24px | 32px | 650 | major section titles |
| `--text-32` | 32px | 38px | 700 | Today hero/date moments |

### Numeric styling

Use tabular numerals for:

- signal IDs
- task scores
- timestamps
- counts

```css
.tabular { font-variant-numeric: tabular-nums; }
```

### Usage examples

```css
.page-title { font-size: 20px; line-height: 28px; font-weight: 600; }
.score-pill { font-size: 12px; line-height: 16px; font-weight: 600; font-variant-numeric: tabular-nums; }
.signal-meta { font-size: 13px; line-height: 18px; color: var(--text-secondary); }
```

## Spacing

Base grid: **4px**

| Token | Value | Use |
|---|---:|---|
| `--space-1` | 4px | tight icon gaps |
| `--space-2` | 8px | chip padding, compact stacks |
| `--space-3` | 12px | row padding |
| `--space-4` | 16px | card padding |
| `--space-5` | 20px | section padding |
| `--space-6` | 24px | column gutters |
| `--space-8` | 32px | page padding |
| `--space-10` | 40px | large section separation |

### Standard component paddings

| Component | Padding |
|---|---|
| Sidebar item | `8px 10px` |
| Dense list row | `10px 12px` |
| Card | `16px` |
| Large panel | `20px` |
| Flyout | `20px` |

### Usage examples

```css
.card { padding: var(--space-4); gap: var(--space-3); }
.page { padding: var(--space-8); }
.filter-bar { gap: var(--space-2); margin-bottom: var(--space-4); }
```

## Radius

Keep corners controlled and desktop-like.

| Token | Value | Use |
|---|---:|---|
| `--radius-sm` | 8px | chips, pills |
| `--radius-md` | 10px | buttons, inputs |
| `--radius-lg` | 14px | cards |
| `--radius-xl` | 18px | palette, major flyouts |

```css
.button { border-radius: var(--radius-md); }
.palette { border-radius: var(--radius-xl); }
```

## Borders and elevation

Minimal shadows. Depth comes mostly from layered panels and 1px separators.

| Token | Value | Use |
|---|---|---|
| `--shadow-sm` | `0 8px 24px rgba(0,0,0,0.18)` | command palette |
| `--shadow-md` | `0 16px 40px rgba(0,0,0,0.24)` | focused flyouts |
| `--ring-accent` | `0 0 0 1px #5E6AD2` | focused cards/input rings |

Rule: default panels should use **border only**. Reserve shadows for overlays.

```css
.panel { border: 1px solid var(--neutral-800); box-shadow: none; }
.flyout { border: 1px solid var(--border-strong); box-shadow: var(--shadow-md); }
```

## Motion

The system uses short, practical motion. State change should feel crisp, not soft.

| Token | Value | Use |
|---|---|---|
| `--ease-out` | `cubic-bezier(0.16, 1, 0.3, 1)` | standard enter/hover |
| `--duration-fast` | `100ms` | hover, row state |
| `--duration-base` | `150ms` | filter toggles, pills, inline reveal |
| `--duration-view` | `200ms` | route/view transitions |
| `--spring-palette` | `type: spring, stiffness: 420, damping: 32` | command palette open |

### Usage examples

```css
.nav-item { transition: background-color var(--duration-fast) var(--ease-out), border-color var(--duration-fast) var(--ease-out); }
.panel-switch { transition: opacity var(--duration-view) var(--ease-out), transform var(--duration-view) var(--ease-out); }
```

## Density

Default density: **dense**

Required preference: **comfortable**

### Dense rules

- list rows: 40–44px minimum
- inputs: 34–36px height
- sidebar items: 32px height
- card padding: 16px

### Comfortable rules

- list rows: 48–52px minimum
- inputs: 40px height
- sidebar items: 38px height
- card padding: 20px

```css
[data-density="dense"] .list-row { min-height: 42px; }
[data-density="comfortable"] .list-row { min-height: 50px; }
```

## Icons

- Use a single icon set, preferably Lucide.
- 16px icons in rows, 18px in nav, 20px in headers.
- Stroke icons only; avoid filled icons except semantic status dots.

## Surfaces and states

### Buttons

| Variant | Visual |
|---|---|
| Primary | accent fill, white text |
| Secondary | panel background, subtle border |
| Ghost | transparent, text only until hover |
| Danger ghost | transparent with danger text |

### Inputs

- panel-colored background
- 1px subtle border
- accent ring on focus
- placeholder in `--text-muted`

### List rows

- default: transparent background
- hover: `--bg-elevated`
- selected: accent-tinted fill + stronger border
- completed/approved: lower opacity but still readable

## Empty and loading states

### Empty states

- always include one next step button
- use concise copy tied to a real backend action

### Skeletons

- use the final block dimensions
- shimmer direction left-to-right
- no height snapping after load

## Example token application

```tsx
<section className="rounded-[14px] border border-[var(--neutral-800)] bg-[var(--bg-panel)] p-4">
  <h2 className="text-[16px] font-semibold text-[var(--text-primary)]">Pending proposals</h2>
  <p className="mt-1 text-[13px] text-[var(--text-secondary)]">Nothing remote executes without approval.</p>
</section>
```
