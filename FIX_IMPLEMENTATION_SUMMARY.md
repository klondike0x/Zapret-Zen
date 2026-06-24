# Fix Implementation Summary: Status Inconsistency Bug

## Date: 2026-06-24

## Problem
The dashboard intermittently shows status "частично" (Partial) instead of "ожидание" (Waiting/Idle) after program startup, especially after PC reboot or when components take longer to start.

## Root Cause
**Race condition** between UI refresh and component startup completion during autostart:

1. At T=900ms: Backend attaches and autostart begins
2. At T=1800ms: Scheduled UI refresh fires
3. At T=1800ms: Components are still starting (zapret takes 6+ seconds)
4. UI sees some components running, others not → shows "Partial" status
5. Components finish starting later, but UI isn't refreshed automatically

## Files Modified

### 1. `src/zapret_zen/ui/main_window.py`

**Changes:**
- Added `self._autostart_in_progress = False` flag (line ~3626)
- Modified `start_enabled_components_async()` to set flag when `autostart_only=True` (line ~7288)
- Modified `_on_master_toggle_finished()` to reset the flag (line ~9569)
- Modified `refresh_dashboard()` to show "Starting" status during autostart (line ~11008-11024)

**Logic:**
```python
# During autostart, prevent showing partial status
if self._autostart_in_progress:
    # Show "Starting" instead of checking individual component states
    self._set_badge("app", self._t("Starting"), "status_warn.svg")
    self._set_badge("zapret", self._t("Starting"), "status_warn.svg")
    self._set_badge("tg", self._t("Starting"), "status_warn.svg")
    return
```

### 2. `src/zapret_zen/services/backend_worker.py`

**Changes:**
- Modified `_handle_start_enabled_components()` to invalidate state cache after startup (line ~369-387)

**Logic:**
```python
# After starting all components
import time
context.processes._invalidate_state_cache()
time.sleep(0.5)  # Give processes time to fully initialize
context.processes._invalidate_state_cache()  # Fresh data
```

### 3. `src/zapret_zen/translations/ru.json`

**Changes:**
- Added translation: `"Starting": "Запуск"` (line ~178)

## How The Fix Works

### Before Fix:
```
T=0ms:    App starts
T=900ms:  Autostart begins → components start in background
T=1800ms: UI refresh → reads states → sees partial completion → shows "Partial"
T=7000ms: Components finish, but UI not refreshed
Result:   User sees "Partial" even though startup is in progress
```

### After Fix:
```
T=0ms:    App starts
T=900ms:  Autostart begins → _autostart_in_progress = True
T=1800ms: UI refresh → sees _autostart_in_progress flag → shows "Starting"
T=7000ms: Components finish → backend callback fires
T=7000ms: _autostart_in_progress = False → UI refreshes → shows correct state
Result:   User sees "Starting" → "Running" (or "Idle" if nothing enabled)
```

## Why Manual Stop/Start Always Worked

Manual start uses `_toggle_in_progress` flag which:
1. Blocks UI refresh during operation
2. Only refreshes after completion signal
3. Always shows correct final state

The fix applies the same pattern to autostart.

## Testing Checklist

- [x] Code changes applied
- [x] Translation added
- [ ] Test: Cold start after PC reboot
- [ ] Test: Normal app restart
- [ ] Test: With slow disk/high CPU load
- [ ] Test: Only zapret enabled
- [ ] Test: Only tg-ws-proxy enabled
- [ ] Test: Both components enabled
- [ ] Test: Manual stop/start still works
- [ ] Test: No components enabled (should show "Idle")

## Expected Behavior After Fix

1. **On startup with autostart enabled:**
   - Shows "Starting" status while components are launching
   - Power button disabled, loading animation shown
   - After ~6-10 seconds, shows "Running" when all components ready
   - Never shows "Partial" during initial startup

2. **On startup without autostart:**
   - Shows "Idle" immediately
   - User can manually start components
   - Behaves as before

3. **Manual stop/start:**
   - No change in behavior
   - Works exactly as before

## Rollback Plan

If issues occur, revert these three files:
```bash
git checkout HEAD -- src/zapret_zen/ui/main_window.py
git checkout HEAD -- src/zapret_zen/services/backend_worker.py
git checkout HEAD -- src/zapret_zen/translations/ru.json
```

## Notes

- Fix is minimal and surgical (3 files, ~30 lines changed)
- No architectural changes
- Follows existing pattern from manual start/stop
- Cache invalidation ensures fresh state data
- Translation follows existing pattern

---

**Status:** Implementation complete, ready for testing  
**Risk Level:** Low (targeted fix, follows existing patterns)  
**Performance Impact:** Negligible (500ms sleep only during autostart)
