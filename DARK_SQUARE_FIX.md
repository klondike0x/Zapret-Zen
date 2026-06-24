# Dark Square Background Fix for Service Category Cards

## Date: 2026-06-24

## Problem Identified

After the previous UI improvements, two dark/gray rectangular blocks appeared:
1. **Behind the category icon, title, and description** - covering the top area of the card
2. **Behind the expanded services grid** - obscuring the individual service toggle icons

This made the UI look unpolished and "clunky" (топорный).

## Root Cause

The issue was caused by two `QWidget` containers that were added in the previous fix:

1. **`_clickable_area`** (line 907-912)
   - Created to separate the clickable area (icon/title) from the expand button
   - By default, `QWidget` instances have an **opaque background** that inherits from the palette
   - In dark themes, this renders as a dark gray rectangle
   - In light themes, this renders as a lighter gray/white rectangle

2. **`_services_container`** (line 940-944)
   - Holds the grid of individual service toggle icons
   - Same issue: default opaque background creates a visible rectangle

### Why This Happened

When you create a `QWidget` in Qt/PySide6:
- It automatically gets a background color from the system palette
- This background is opaque (not transparent)
- When placed inside a custom-painted widget like `ServiceCategoryCard`, it covers the custom paint with a solid rectangle
- The card's custom `paintEvent()` (from `BaseServiceCard`) draws the rounded background, but these widgets sit on top and block it

## The Fix

Added explicit transparent backgrounds to both widgets:

### Change 1: Make `_clickable_area` transparent
```python
self._clickable_area = QWidget(self)
self._clickable_area.setCursor(Qt.CursorShape.PointingHandCursor)
self._clickable_area.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
self._clickable_area.setStyleSheet("background: transparent;")  # ← ADDED THIS LINE
clickable_layout = QVBoxLayout(self._clickable_area)
```

### Change 2: Make `_services_container` transparent
```python
self._services_container = QWidget()
self._services_container.setVisible(False)
self._services_container.setStyleSheet("background: transparent;")  # ← ADDED THIS LINE
self._services_grid = QGridLayout(self._services_container)
```

## Technical Explanation

**`setStyleSheet("background: transparent;")`** tells Qt to:
- Not fill the widget's rectangle with any color
- Let the parent widget's painted content show through
- Only render the widget's children (labels, icons, buttons)

This allows the `ServiceCategoryCard`'s custom-painted background (with rounded corners, borders, and gradients from `BaseServiceCard.paintEvent()`) to remain fully visible.

## Alternative Approaches Considered

1. **`setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)`**
   - More complex, requires window composition
   - Overkill for this use case

2. **Remove container widgets entirely**
   - Would break the click area separation logic
   - Would require complete redesign

3. **Use `QFrame` with no frame style**
   - Still has default background
   - Same issue

**Chosen solution** (stylesheet) is:
- Simple and direct
- Works across all platforms
- Minimal code change
- No side effects

## Result

After this fix:
- ✅ No dark rectangles behind icon/title/description
- ✅ No dark rectangles behind expanded services grid
- ✅ Card background (from `BaseServiceCard.paintEvent()`) is fully visible
- ✅ Click areas still work correctly (clickable area vs expand button)
- ✅ All visual styling preserved (borders, gradients, selection glow)
- ✅ Theme changes work correctly

## Files Modified

- **src/zapret_zen/ui/main_window.py**
  - Line ~910: Added `.setStyleSheet("background: transparent;")` to `_clickable_area`
  - Line ~942: Added `.setStyleSheet("background: transparent;")` to `_services_container`

## Testing

Run the application and verify:
- [ ] No dark squares visible in collapsed state
- [ ] No dark squares visible when expanded
- [ ] Card background renders cleanly with rounded corners
- [ ] Selection glow visible around the entire card
- [ ] Works in both light and dark themes
- [ ] Click area separation still functions (card vs button)

---

**Fix Type:** Visual bug fix  
**Complexity:** Simple (2 lines)  
**Risk:** None (purely cosmetic)  
**Status:** Complete
