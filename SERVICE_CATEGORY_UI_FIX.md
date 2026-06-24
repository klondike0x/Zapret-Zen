# Service Category Card UI Fix Summary

## Date: 2026-06-24

## Problems Fixed

### 1. **Ugly and Too-Small Expand Button**
**Before:** 22×22px QToolButton with tiny arrow, hard to see and click
**After:** 140×32px QPushButton with clear text label "Show services" / "Hide services"

**Changes:**
- Changed from `QToolButton` with arrow to `QPushButton` with text
- Increased size from 22×22 to 140×32 pixels
- Centered horizontally in the card
- Added proper styling with background colors, hover effects, and accent color when expanded

### 2. **Expand Button Toggled Category Instead of Showing Services**
**Before:** Clicking anywhere on the card (including the expand button) would toggle the entire category ON/OFF
**After:** Clear separation between clickable areas

**Changes:**
- Created `_clickable_area` widget that wraps only the icon, title, and description
- Card click now only works within this clickable area
- Expand button is outside the clickable area, so it only expands/collapses the services list
- Added `mousePressEvent` and updated `mouseReleaseEvent` to check if click is within clickable area

### 3. **Redundant Service Name Text List**
**Before:** Card displayed a frame with comma-separated service names (e.g., "ServiceA, ServiceB, ServiceC...")
**After:** Text list completely removed

**Changes:**
- Removed `_members_frame`, `_members_label` widgets from layout
- Updated `set_texts()` to only accept `title` and `description` (removed `members_text` parameter)
- Removed all references to members text throughout the codebase
- Can remove `_category_card_members_text()` method entirely (currently unused)

## Implementation Details

### New Layout Structure
```
ServiceCategoryCard
├── _clickable_area (QWidget) ← Click here toggles category ON/OFF
│   ├── icon + checkmark (top row)
│   ├── title
│   └── description
├── _services_container (hidden by default)
│   └── _services_grid (4-column grid of ServiceToggleIcon widgets)
├── stretch
└── expand button (centered) ← Click here shows/hides service list
```

### Expand Button Styling
**Collapsed state:**
- Light theme: Light gray background, dark text
- Dark theme: Semi-transparent white background, light text
- Button text: "Show services"

**Expanded state:**
- Background: Accent color
- Text: White
- Button text: "Hide services"

**Hover/Press:**
- Lighter/darker shade of current background color
- Smooth visual feedback

### Click Handling
```python
def mouseReleaseEvent(self, event):
    if click is within _clickable_area:
        # Toggle entire category ON/OFF
        self.toggled.emit(category.id, not self._selected)
    else:
        # Ignore (button has its own handler)

def _toggle_expand(self):
    # Only show/hide services container
    # Does NOT affect selection state
```

## Files Modified

1. **src/zapret_zen/ui/main_window.py**
   - `ServiceCategoryCard.__init__()` - Restructured layout
   - `set_texts()` - Removed members_text parameter
   - `mouseReleaseEvent()` - Added clickable area detection
   - `mousePressEvent()` - Added for proper click handling
   - `_toggle_expand()` - Changed to update button text instead of arrow
   - `_sync_style()` - Removed members styling, calls new method
   - `_sync_expand_button_style()` - New method for button styling
   - All calls to `set_texts()` - Removed third parameter

## Testing Checklist

- [x] Code changes applied
- [ ] Test: Click card (icon/title area) toggles category ON/OFF
- [ ] Test: Click expand button shows/hides service grid
- [ ] Test: Expand button does NOT toggle category state
- [ ] Test: Button text changes between "Show services" and "Hide services"
- [ ] Test: Button styling changes when expanded (accent color background)
- [ ] Test: Hover effects work properly
- [ ] Test: Individual service toggles work correctly when expanded
- [ ] Test: Theme changes (light/dark) apply correct colors
- [ ] Test: No redundant service name text appears below the card

## Visual Improvements

1. **Cleaner Design**: No cluttered text list of service names
2. **Better Usability**: Large, obvious button with clear label
3. **Proper Separation**: Card click vs button click are distinct actions
4. **Modern Look**: Rounded corners, proper spacing, accent color highlights
5. **Clear Feedback**: Button changes color and text when expanded

## Notes

- The `_category_card_members_text()` method at line ~5962 is now unused and can be safely deleted if desired
- Expand state is preserved when theme changes (handled by `_sync_expand_button_style()`)
- The services grid spacing increased from 4px to 6px for better visual separation
- Container margins increased from 4px to 8px (top/bottom) for breathing room

---

**Status:** All fixes implemented and ready for testing  
**Risk Level:** Low (structural changes but well-isolated to ServiceCategoryCard)
