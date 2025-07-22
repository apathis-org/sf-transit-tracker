# SF Transit Tracker - Theme System

This directory contains the theme files for the SF Transit Tracker application.

## Theme Structure

### Default Theme (`default/`)
- **default-theme.css** - Complete original styling (black background, simple panels, standard colors)
- **Description**: Clean, professional look matching the original application design
- **Status**: ✅ Complete and working

### TRON Theme (`tron/`)
- **tron-theme.css** - Main TRON theme with CSS variables and cyberpunk colors
- **tron-vehicles.css** - Vehicle icons with glowing effects and gradients  
- **tron-animations.css** - Animation effects (pulse, glow, grid backgrounds)
- **tron-panels.css** - Panel styling with backdrop effects
- **tron-components.css** - Component-specific TRON styling
- **Description**: Cyberpunk aesthetic with glowing effects, animated backgrounds, sharp edges
- **Status**: 🔄 Preserved for future integration (Phase 3)

## Implementation Plan

### Phase 2 (Current)
- ✅ Use default theme for modular frontend
- ✅ Ensure exact visual parity with original
- ✅ Preserve TRON theme files for later

### Phase 3 (Future)
- 🔮 Implement theme switching system
- 🔮 Add theme toggle button in UI
- 🔮 Enable runtime theme switching
- 🔮 Add theme persistence (localStorage)

## Usage

### Default Theme
```html
<link rel="stylesheet" href="/static/themes/default/default-theme.css">
```

### TRON Theme (Future)
```html
<link rel="stylesheet" href="/static/themes/tron/tron-theme.css">
<link rel="stylesheet" href="/static/themes/tron/tron-vehicles.css">
<link rel="stylesheet" href="/static/themes/tron/tron-animations.css">
<link rel="stylesheet" href="/static/themes/tron/tron-panels.css">
<link rel="stylesheet" href="/static/themes/tron/tron-components.css">
```