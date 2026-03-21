# Design System Specification: Liquid Glass & iOS 26

## 1. Overview & Creative North Star
**Creative North Star: "The Kinetic Prism"**

This design system rejects the static, flat nature of traditional web interfaces in favor of a living, breathing digital ecosystem. Inspired by high-end automotive finishes and futuristic OS depth, the "Kinetic Prism" philosophy treats the screen as a thick pane of polished obsidian infused with liquid light. 

To break the "template" look, we move away from rigid grids and move toward **Intentional Overlap**. Elements should feel as though they are floating in a pressurized, fluid environment. By utilizing extreme corner radii (`24px/1.5rem`), heavy backdrop blurs, and metallic accents, we create an experience that feels premium, energetic, and impossibly high-tech.

---

## 2. Colors & Surface Philosophy
The palette is anchored by **Cosmic Orange**, a high-chroma, metallic hue that serves as our primary energy source against a void of **Deep Obsidian**.

### The "No-Line" Rule
**Borders are strictly prohibited for sectioning.** To define boundaries, use tonal shifts between `surface` tiers or `backdrop-filter: blur(40px)`. A section change is signaled by moving from `surface-container-low` to `surface-container-high`, never by a 1px solid line.

### Surface Hierarchy & Nesting
Treat the UI as a physical stack of glass.
- **Base Layer:** `surface` (#0e0e0e) – The infinite void.
- **Sectioning:** `surface-container-low` (#131313) – Large structural areas.
- **Interactive Cards:** `surface-container-highest` (#262626) – Floating interactive elements.
- **Glass Overlays:** Use `surface-variant` at 40% opacity with a `blur-3xl` effect to create "Liquid Glass" panels that let the background colors bleed through organically.

### Signature Textures
Main CTAs and Hero moments must utilize **Sunset Gradients**. Move from `primary` (#ff906d) to `tertiary_container` (#f9873e) at a 135-degree angle. This creates a "metallic" sheen that mimics light hitting a curved glass surface.

---

## 3. Typography
We utilize **Plus Jakarta Sans** for its geometric precision and tech-forward legibility.

*   **Display (Display-LG/MD):** Used for "Hero" moments. Set with `-0.04em` letter spacing and `1.1` line height. These should feel like editorial headlines in a luxury tech magazine.
*   **Headlines (Headline-SM/MD):** The primary navigational anchors. Use `on_surface` (#ffffff) to ensure high contrast against the obsidian background.
*   **Body (Body-MD):** Use `on_surface_variant` (#adaaaa) for long-form text. The slight grey reduction prevents visual fatigue on high-brightness OLED displays.
*   **Labels (Label-MD/SM):** Always uppercase with `+0.05em` letter spacing when used for metadata or category tags, reinforcing the "high-tech" instrument aesthetic.

---

## 4. Elevation & Depth
Depth in this system is a result of **Tonal Layering** and light simulation, not artificial drop shadows.

*   **The Layering Principle:** Place a `surface_container_highest` card inside a `surface_container_low` parent. The 12% difference in lightness provides a "natural lift" that feels architectural.
*   **Liquid Glows:** For floating elements, use a `primary` tinted shadow. Instead of `#000000`, use `on_primary_container` (#460f00) at 10% opacity with a `64px` blur.
*   **The Ghost Border:** If accessibility requires a stroke (e.g., input focus), use `outline_variant` (#484847) at **20% opacity**. It should be felt, not seen.
*   **Inner Glow:** To achieve the "Liquid Glass" look, apply a `1px` inner-shadow (inset) using `on_surface` at 15% opacity to the top and left edges of glass containers. This mimics the light-catching edge of a glass pane.

---

## 5. Components

### Buttons (The Kinetic Triggers)
*   **Primary:** Gradient fill (`primary` to `primary_container`). `24px` rounding. No border. On hover, apply a `subtle inner glow`.
*   **Secondary:** `surface_container_highest` fill with a `Ghost Border`. Text color is `primary`.
*   **Tertiary:** Transparent background, `label-md` type, with a `primary` underline that expands from the center on hover.

### Liquid Inputs
*   **Field:** `surface_container_low` background, `24px` rounding, `1.4rem` vertical padding. 
*   **States:** On focus, the background shifts to `surface_container_high` and a subtle `Cosmic Orange` glow appears at the base.
*   **Error:** Use `error_dim` (#d7383b) for text and a 10% opaque `error` fill for the container background.

### Glass Cards & Lists
*   **Constraint:** No dividers. Use `Spacing-6` (2rem) of vertical white space to separate list items.
*   **Visual Interest:** Use `surface-variant` with `backdrop-filter: blur(24px)`. Elements behind the card should be visible but diffused, creating an "iOS 26" depth effect.

### Selection Chips
*   **Unselected:** `surface_container_highest` with `on_surface_variant` text.
*   **Selected:** `primary` background with `on_primary` (#5b1600) text. The transition must be a "liquid" morph effect.

---

## 6. Do’s and Don’ts

### Do:
*   **Do** use asymmetrical layouts. For example, a `display-lg` headline should be offset from the main grid to create an editorial feel.
*   **Do** use the `24px` (1.5rem) rounding consistently. Even small tags should feel like rounded pebbles.
*   **Do** embrace the "Obsidian" void. Large areas of `#0e0e0e` make the `Cosmic Orange` accents feel more premium.

### Don’t:
*   **Don't** use 1px solid borders to separate content. It breaks the "Liquid Glass" illusion.
*   **Don't** use pure black (#000000) for anything other than the `surface_container_lowest`. It kills the depth of the glass effect.
*   **Don't** use standard easing. Use `cubic-bezier(0.2, 0.8, 0.2, 1)` for all transitions to mimic the movement of heavy fluid.