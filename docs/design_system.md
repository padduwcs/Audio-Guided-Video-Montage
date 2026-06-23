# Design System Inspired by Apple

## 1. Visual Theme & Atmosphere

Apple's design system embodies minimalist elegance paired with sophisticated restraint. The aesthetic prioritizes clarity and intuitive navigation through generous whitespace, refined typography, and a carefully orchestrated color palette dominated by deep neutrals and vibrant accents. The system exudes premium quality through precise spacing, deliberate hierarchy, and subtle depth—creating an atmosphere of innovation tempered by accessibility. Every interface element serves a purpose, with ornamental design eliminated in favor of functional beauty. The visual language conveys confidence and approachability simultaneously, making complex technology feel intuitive and welcoming.

*Key Characteristics*
- Minimalist and purpose-driven layout philosophy
- Dominant neutral palette with strategic blue accent highlights
- Large, breathing whitespace that emphasizes content
- Precision typography as primary visual hierarchy tool
- Soft, frosted-glass surfaces with subtle transparency layers
- Touch-first interaction paradigms balanced with desktop elegance
- Generous padding and spacing throughout all components
- Clear visual distinction between interactive and static elements

## 2. Color Palette & Roles

### Primary

- *Primary Action Blue* (#0071E3): Used for primary call-to-action buttons, active states, and critical interactive elements requiring immediate user attention
- *Primary Blue Hover* (#006EDB): Interactive state for primary blue elements when hovered or focused
- *Primary Blue Press* (#0076DF): Pressed/active state for primary blue interactive elements

### Interactive

- *Interactive Blue Deep* (#0077ED): Specialized accent for specific interactive contexts and secondary prominence elements

### Neutral Scale

- *Text Dominant* (#1D1D1F): Primary text color for all body copy, headings, and standard text content—used most frequently throughout the system
- *Text Secondary* (#333336): Secondary text for less emphasized content, subheadings, and supporting information
- *Text Tertiary* (#6E6E73): Tertiary text for captions, timestamps, and minimal-emphasis supporting text
- *Text Inverse* (#000000): Pure black for maximum contrast scenarios and critical emphasis
- *Neutral Lightest* (#FFFFFF): Pure white for backgrounds and content surfaces
- *Neutral Dark Medium* (#272729): Dark neutral for subtle backgrounds and card bases
- *Neutral Dark Deep* (#18181A): Deep neutral for premium dark mode or high-contrast backgrounds

### Surface & Borders

- *Surface Light* (#EDEDF2): Subtle background for bordered containers, dividers, and light surface differentation
- *Navigation Surface* (rgba(255, 255, 255, 0.8)): Semi-transparent white surface for floating navigation bars with frosted-glass effect
- *Border Implicit* (rgba(0, 0, 0, 0.56)): Soft implicit border color for subtle visual separation
- *Overlay Soft* (rgba(0, 0, 0, 0.8)): Semi-transparent dark overlay for secondary text and muted contexts

## 3. Typography Rules

### Font Family

*Primary:* SF Pro Text, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif

*Secondary:* SF Pro Display, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif

### Hierarchy

| Role | Font | Size | Weight | Line Height | Letter Spacing | Notes |
|------|------|------|--------|-------------|----------------|-------|
| Display Hero | SF Pro Display | 40px | 600 | 44px | 0px | Large hero headlines on landing pages and feature sections |
| Heading Large | SF Pro Display | 28px | 400 | 32px | 0px | Major section headings and primary card titles |
| Heading Primary | SF Pro Display | 24px | 600 | 28px | 0px | Card headlines and prominent content headers |
| Heading Secondary | SF Pro Text | 34px | 600 | 50px | 0px | Large subheadings and prominent titles |
| Body Default | SF Pro Text | 17px | 400 | 25px | 0px | Standard paragraph text and body content |
| Body Compact | SF Pro Text | 17px | 400 | 21px | 0px | Navigation links and compact text elements |
| Small Label | SF Pro Text | 12px | 400 | 16px | 0px | Caption, meta information, and supporting labels |
| Eyebrow | SF Pro Text | 12px | 400 | 16px | 0px | Descriptive labels above headings |
| Button | SF Pro Text | 17px | 400 | 25px | 0px | Primary and secondary button text |
| Link | SF Pro Text | 17px | 600 | 21px | 0px | Interactive link text with weight emphasis |
| Code | SF Pro Text | 13px | 400 | 20px | 0px | Monospaced code blocks and technical content |

### Principles

- Typography establishes visual hierarchy through weight and scale rather than color differentiation
- Line height maintains generous vertical rhythm, improving readability across screen sizes
- Font weight progression (400 → 600 → 700) creates clear distinction between content importance levels
- SF Pro system fonts ensure platform-native rendering and accessibility optimization
- Text color inherits semantic meaning from palette, not from typography role alone
- Generous line heights reduce cognitive load on long-form content

## 4. Component Stylings

### Buttons

#### Primary Button
- *Background:* #0071E3
- *Text Color:* #FFFFFF
- *Font:* SF Pro Text, 17px, weight 400, line-height 25px
- *Padding:* 12px 24px
- *Border Radius:* 50%
- *Border:* none
- *Box Shadow:* none
- *Hover State:* Background #006EDB
- *Active State:* Background #0076DF
- *Height:* 44px (minimum touch target)
- *Width:* auto (content-dependent)

#### Secondary Button
- *Background:* transparent
- *Text Color:* #0071E3
- *Font:* SF Pro Text, 17px, weight 400, line-height 25px
- *Padding:* 12px 24px
- *Border Radius:* 50%
- *Border:* 2px solid #0071E3
- *Box Shadow:* none
- *Hover State:* Background rgba(0, 113, 227, 0.05), Border Color #006EDB
- *Active State:* Border 2px solid #0076DF
- *Height:* 44px
- *Width:* auto

#### Ghost Button
- *Background:* transparent
- *Text Color:* #1D1D1F
- *Font:* SF Pro Text, 17px, weight 400, line-height 25px
- *Padding:* 12px 8px
- *Border Radius:* 0px
- *Border:* none
- *Box Shadow:* none
- *Hover State:* Background rgba(0, 0, 0, 0.05)
- *Active State:* Background rgba(0, 0, 0, 0.08)
- *Height:* 44px
- *Width:* auto

### Cards & Containers

#### Hero Card
- *Background:* #FFFFFF
- *Text Color:* #1D1D1F
- *Font:* SF Pro Display, 40px, weight 600, line-height 44px
- *Padding:* 48px
- *Border Radius:* 0px
- *Border:* none
- *Box Shadow:* none
- *Min Height:* 580px
- *Max Width:* 1262px

#### Feature Card
- *Background:* rgba(0, 0, 0, 0)
- *Text Color:* #1D1D1F
- *Font:* SF Pro Text, 17px, weight 400, line-height 25px
- *Padding:* 32px 40px
- *Border Radius:* 0px
- *Border:* 1px solid #EDEDF2
- *Box Shadow:* none

#### Label Card (Meta)
- *Background:* transparent
- *Text Color:* rgba(0, 0, 0, 0.56)
- *Font:* SF Pro Text, 12px, weight 400, line-height 16px
- *Padding:* 8px 0px
- *Border Radius:* 0px
- *Border:* none
- *Box Shadow:* none

### Navigation

#### Top Navigation Bar
- *Background:* rgba(255, 255, 255, 0.8)
- *Text Color:* #1D1D1F
- *Font:* SF Pro Text, 17px, weight 400, line-height 25px
- *Padding:* 0px 20px
- *Border Radius:* 0px
- *Border:* 1px solid rgba(0, 0, 0, 0.1)
- *Box Shadow:* none
- *Height:* 44px
- *Width:* 100%
- *Nav Item Padding:* 0px 8px
- *Hover State:* Text Color #0071E3

#### Navigation Link
- *Background:* transparent
- *Text Color:* rgba(0, 0, 0, 0.8)
- *Font:* SF Pro Text, 17px, weight 600, line-height 21px
- *Padding:* 0px 8px
- *Border Radius:* 0px
- *Border:* none
- *Box Shadow:* none
- *Height:* 44px
- *Hover State:* Text Color #0071E3
- *Active State:* Text Color #0071E3

### Inputs & Forms

#### Text Input
- *Background:* #FFFFFF
- *Text Color:* #1D1D1F
- *Placeholder Color:* #6E6E73
- *Font:* SF Pro Text, 17px, weight 400, line-height 25px
- *Padding:* 12px 16px
- *Border Radius:* 8px
- *Border:* 1px solid #D5D5D7
- *Box Shadow:* none
- *Height:* 44px
- *Focus State:* Border Color #0071E3, Box Shadow 0 0 0 3px rgba(0, 113, 227, 0.1)

#### Form Label
- *Font:* SF Pro Text, 12px, weight 600, line-height 16px
- *Text Color:* #1D1D1F
- *Margin Bottom:* 8px
- *Display:* block

### Links

#### Standard Link
- *Text Color:* #0071E3
- *Font:* SF Pro Text, 17px, weight 600, line-height 21px
- *Text Decoration:* none
- *Hover State:* Text Color #006EDB, Text Decoration underline
- *Active State:* Text Color #0076DF

#### Subtle Link
- *Text Color:* rgba(0, 0, 0, 0.8)
- *Font:* SF Pro Text, 17px, weight 400, line-height 25px
- *Text Decoration:* none
- *Hover State:* Text Color #0071E3

## 5. Layout Principles

### Spacing System

*Base Unit:* 4px

*Scale:*
- 8px — Compact padding for inline elements and tight spacing
- 12px — Small margin between related components
- 16px — Standard padding for content containers
- 20px — Default margin between sections
- 24px — Comfortable padding for card interiors
- 28px — Large spacing for major section separation
- 32px — Premium padding for feature cards
- 40px — Extra-large padding for hero sections
- 44px — Vertical rhythm base and touch target height
- 48px — Hero section internal spacing
- 52px — Extra-large gaps between major sections
- 56px — Maximum section separation

*Usage Context:*
- Components typically use 24px–32px internal padding
- Sections separated by 40px–56px vertical margin
- Navigation and buttons maintain 44px height minimum for touch
- Hero sections employ 48px–56px padding
- Inline spacing follows 8px–12px increments

### Grid & Container

- *Max Container Width:* 1262px (measured from hero card)
- *Column Strategy:* Flexible grid adapting to content; typically 1–3 columns on desktop
- *Section Pattern:* Full-width sections with centered max-width containers
- *Gutter:* 20px–24px between columns
- *Margin Symmetry:* Equal left/right margins maintaining visual centering

### Whitespace Philosophy

Apple's design prioritizes negative space as an active design element. Whitespace reduces cognitive load, emphasizes content, and creates visual hierarchy without additional visual decoration. The system uses generous padding and margins to ensure components never feel cramped. Empty space is intentional and contributes to perceived premium quality.

### Border Radius Scale

- 0px — Cards, containers, and large surfaces maintain sharp corners for clarity
- 8px — Input fields and form elements for approachability
- 50% — Buttons for iconic, contained interaction targets

## 6. Depth & Elevation

| Level | Treatment | Use |
|-------|-----------|-----|
| Flat (None) | No shadow, solid backgrounds | Standard cards, text, and primary content surfaces |
| Subtle (Raised) | box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12) | Floating buttons and secondary surfaces |
| Medium (Floating) | box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) | Modals, popovers, and prominent overlays |
| Deep (Emphasis) | box-shadow: 0 12px 32px rgba(0, 0, 0, 0.16) | High-priority modals and critical overlays |

*Shadow Philosophy:*

Apple's elevation system uses minimal shadows to maintain clarity. Shadows are achieved through subtle blur and opacity rather than hard offsets, creating soft depth perception. Semi-transparent navigation bars use frosted-glass effects (background blur with slight transparency) to establish layering without heavy shadows. Depth is primarily conveyed through color, positioning, and scale rather than dramatic shadows.

## 7. Do's and Don'ts

### Do

- Use #0071E3 exclusively for primary interactive elements requiring user attention
- Maintain 44px minimum height for all touch-target buttons and navigation elements
- Apply generous padding (24px–48px) inside major containers to prevent visual crowding
- Stack sections with 40px–56px vertical margin for clear visual separation
- Use SF Pro Text for body content and SF Pro Display for prominent headlines
- Implement semi-transparent navigation surfaces with backdrop blur for depth
- Maintain consistent 50% border radius exclusively for button elements
- Group related content within subtle borders (1px solid #EDEDF2) rather than heavy shadows
- Employ text color hierarchy (primary → secondary → tertiary) to establish reading order
- Scale typography by weight (400 → 600) before increasing font size for hierarchy

### Don't

- Use shadows as the primary depth mechanism; favor flat design with subtle treatment
- Exceed 1262px container width on desktop to maintain comfortable content width
- Apply borders to all card types; reserve borders for secondary grouping
- Mix multiple accent colors; #0071E3 and its states suffice for all interactive elements
- Reduce padding below 12px in standard contexts; whitespace is intentional
- Apply rounded corners to large containers; reserve rounded corners for specific elements like buttons and inputs
- Exceed 600 font weight for body text; weight escalation creates hierarchy
- Use more than 2–3 font sizes in a single layout section
- Stack components without clear spacing; maintain minimum 12px margin between elements
- Employ color alone to communicate hierarchy; combine color with typography weight and scale

## 8. Responsive Behavior

### Breakpoints

| Breakpoint | Width | Key Changes |
|------------|-------|------------|
| Mobile | 320px–767px | Single column, full-width containers, increased padding, large touch targets |
| Tablet | 768px–1023px | Two-column layouts, reduced padding (24px–32px), optimized for portrait/landscape |
| Desktop | 1024px–1440px | Three-column layouts, max-width 1262px container, standard padding |
| Large Desktop | 1441px+ | Three-column layouts maintained, centered container with symmetric margins |

### Touch Targets

- *Minimum Height:* 44px for all interactive elements (buttons, links, navigation items)
- *Minimum Width:* 44px for button and clickable icons
- *Padding Around Target:* Minimum 8px between adjacent touch targets
- *Hover Zone Expansion:* 8px padding around target expands effective touch area on hover
- *Mobile Optimization:* Touch targets at screen bottom include additional 16px bottom margin for thumb accessibility

### Collapsing Strategy

- *Navigation:* Hamburger menu activation below 768px; collapse primary nav items into drawer
- *Grid Columns:* Reduce from 3 columns (desktop) → 2 columns (tablet) → 1 column (mobile)
- *Hero Sections:* Reduce padding from 48px (desktop) → 32px (tablet) → 24px (mobile)
- *Typography:* Reduce Display role sizes by 8–12px on tablet, 12–16px on mobile
- *Spacing:* Reduce all margins by 25% on tablet, 50% on mobile (minimum 8px)
- *Container Padding:* Maintain horizontal padding minimum of 16px on mobile

## 9. Agent Prompt Guide

### Quick Color Reference

- *Primary CTA:* Primary Action Blue (#0071E3)
- *Primary CTA Hover:* Primary Blue Hover (#006EDB)
- *Primary CTA Active:* Primary Blue Press (#0076DF)
- *Primary Text:* Text Dominant (#1D1D1F)
- *Secondary Text:* Text Secondary (#333336)
- *Tertiary Text / Captions:* Text Tertiary (#6E6E73)
- *Background:* Neutral Lightest (#FFFFFF)
- *Surface / Card Borders:* Surface Light (#EDEDF2)
- *Navigation Background:* Navigation Surface (rgba(255, 255, 255, 0.8))
- *Overlay / Muted Text:* Overlay Soft (rgba(0, 0, 0, 0.8))
- *Dark Surface:* Neutral Dark Medium (#272729)

### Iteration Guide

1. **All interactive elements use #0071E3 for primary actions.** Hover states transition to #006EDB, active states to #0076DF. No other accent colors exist in the primary palette.

2. *Button minimum height is 44px.* All buttons use 50% border radius. Primary buttons are filled blue; secondary buttons have blue borders with transparent background; ghost buttons have no border and neutral text.

3. *Maintain spacing hierarchy:* 24px–32px internal padding for cards, 40px–56px between sections. Minimum 12px margins between adjacent components. Never use padding smaller than 8px except for inline spacing.

4. *Typography uses two font families:* SF Pro Display for headlines (24px–40px, weight 600) and SF Pro Text for body (12px–17px, weight 400–600). Line height scales proportionally; larger text uses proportionally larger line height.

5. *Cards and containers use sharp corners (0px radius) except buttons (50% radius) and inputs (8px radius).* Borders on cards are optional; use 1px solid #EDEDF2 only for secondary grouping.

6. **Navigation bars use semi-transparent white (rgba(255, 255, 255, 0.8)) with frosted-glass effect.** Standard cards use solid white (#FFFFFF). No drop shadows on primary surfaces; reserve subtle shadows for floating modals only.

7. *Text hierarchy prioritizes weight escalation over size growth.* Body text is 17px weight 400; headlines increase to weight 600–700 before increasing size. Captions and labels are 12px weight 400.

8. *Neutral palette dominates:* #1D1D1F for primary text (used 563+ times), #333336 for secondary, #6E6E73 for captions. These colors paired with generous whitespace create the system's premium aesthetic.

9. *Responsive collapsing:* Mobile uses single columns with increased padding (24px–32px). Tablet uses two columns with moderate padding (32px). Desktop uses three columns with standard max-width 1262px container. All text sizes reduce proportionally on mobile by 12–16px.

10. *Every interactive element respects 44px touch minimum.* Navigation items, buttons, and links all maintain 44px height. Input fields are 44px tall with 16px horizontal padding. Spacing between touch targets is minimum 8px on mobile, 12px on desktop.