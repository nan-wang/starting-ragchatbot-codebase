# Frontend Changes: Dark/Light Theme Toggle

## Summary

Added a theme toggle button in the top-right corner of the chat area that allows users to switch between dark and light modes. The button uses sun/moon icons with smooth animated transitions.

## Files Modified

### `frontend/index.html`
- Added a theme toggle `<button>` element inside `.chat-main` with:
  - Sun SVG icon (shown in dark mode, click to switch to light)
  - Moon SVG icon (shown in light mode, click to switch to dark)
  - `aria-label` and `title` attributes for accessibility

### `frontend/style.css`
- **Light theme CSS variables**: Added `[data-theme="light"]` selector with a full set of light-mode color overrides (`--background: #f8fafc`, `--surface: #ffffff`, `--text-primary: #0f172a`, etc.)
- **Smooth transitions**: Added `transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease` to body and key UI elements (sidebar, chat area, inputs, messages, buttons)
- **Light-mode overrides for hardcoded values**: Added `[data-theme="light"]` selectors for `.message-content code` and `.message-content pre` to reduce their background opacity, and ensured user message text stays white
- **Toggle button styles**: Circular 40px button with `position: absolute; top: 1rem; right: 1.5rem`, hover scale effect, focus ring, and active press animation
- **Icon animation**: Sun and moon icons crossfade with rotation transforms (90deg/-90deg) via `opacity` and `transform` transitions on `[data-theme="light"]`
- **Positioning**: Added `position: relative` to `.chat-main` to contain the absolutely-positioned toggle

### `frontend/script.js`
- **`themeToggle` DOM reference**: Added to the global variables and `DOMContentLoaded` initialization
- **`initTheme()`**: Called on page load; reads `localStorage.getItem('theme')` for saved preference, falls back to `window.matchMedia('(prefers-color-scheme: light)')` for system preference, defaults to dark
- **`toggleTheme()`**: Reads current `data-theme` attribute, flips between dark/light, saves to `localStorage`
- **`setTheme(theme)`**: Sets or removes the `data-theme="light"` attribute on `<html>`, updates `aria-label` on the toggle button for screen readers
- **Event listener**: Added click handler for the toggle button in `setupEventListeners()`

## Design Decisions

- **Dark mode is the default** to match the existing UI, with light mode as the opt-in
- **System preference detection** via `prefers-color-scheme` media query on first visit
- **`localStorage` persistence** so the preference survives page reloads
- **CSS custom properties** (`data-theme` on `<html>`) for the theming mechanism, requiring zero JavaScript for style application
- **Icon-based design** using inline SVG (sun/moon from Feather Icons) so no external icon library is needed
- **Keyboard accessible**: Button is natively focusable with visible focus ring via `box-shadow`
