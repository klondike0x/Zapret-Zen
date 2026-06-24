# Bug Analysis Report: Status Inconsistency - "частично" (Partial) Instead of "ожидание" (Waiting)

## Executive Summary

**Root Cause Found:** Race condition between component startup execution and UI state refresh during autostart.

**Location:** `src/zapret_zen/app.py:332-356` and `src/zapret_zen/ui/main_window.py:11011-11018`

**Impact:** Intermittent - occurs when UI refresh happens **during** the component startup sequence, before all components finish starting.

---

## Detailed Analysis

### 1. The Race Condition Sequence

#### **On Autostart Launch (with `auto_run_components=True`):**

**Timeline:**

```
T=0ms:    Window.show() is called (app.py:344)
T=900ms:  Backend attaches (app.py:358)
T=900ms:  Autostart callback fires → start_enabled_components_async(autostart_only=True)
T=900ms:  UI marks dirty and schedules refresh (main_window.py:7291)
T=900ms:  Backend worker starts components in background thread
T=900ms:  Components start sequentially: zapret starts (takes 6+ seconds)
T=1800ms: SCHEDULED UI REFRESH FIRES (main_window.py:4510) ← **PROBLEM HERE**
T=1800ms: refresh_dashboard() reads component states
T=1800ms: zapret is still starting (status="running" but incomplete)
T=1800ms: tg-ws-proxy hasn't started yet (status="stopped")
T=1800ms: UI sees: active_ids=['zapret','tg-ws-proxy'], running_ids=['zapret']
T=1800ms: Result: any_running=True, fully_running=False → STATUS = "PARTIAL"
T=7000ms: zapret finishes starting, tg-ws-proxy starts
T=8000ms: All components actually running, but UI not refreshed yet
```

**Key Issue:** The UI refresh at **T=1800ms** (from `_schedule_startup_refresh`) happens **before** components finish starting.

---

### 2. Code Evidence

#### **File: `src/zapret_zen/app.py:332-356`**
```python
if known.autostart_launch and settings.auto_run_components:
    def _start_after_backend() -> None:
        if context.backend is not None:
            window.start_enabled_components_async(autostart_only=True)  # ← Starts components
    autostart_callback = _start_after_backend
else:
    autostart_callback = None

# ...

def _attach_backend_after_show() -> None:
    backend = BackendWorkerClient(app)
    context.backend = backend
    window.attach_backend_client(backend)
    if autostart_callback is not None:
        autostart_callback()  # ← Called at T=900ms

QTimer.singleShot(900, _attach_backend_after_show)  # ← Scheduled at T=900ms
```

#### **File: `src/zapret_zen/ui/main_window.py:4489-4510`**
```python
def _schedule_startup_refresh(self) -> None:
    # ...
    def _refresh_rest() -> None:
        if not self._backend_attached:
            QTimer.singleShot(300, _refresh_rest)
            return
        self._mark_dirty("dashboard", "services", "components", "mods", "files", "logs", "tray")
    
    QTimer.singleShot(900, _refresh_current)
    QTimer.singleShot(1800, _refresh_rest)  # ← UI REFRESHES AT T=1800ms
```

#### **File: `src/zapret_zen/ui/main_window.py:11011-11032`**
```python
def refresh_dashboard(self) -> None:
    # ...
    states = self._component_states()
    components = self._component_defs()
    active_ids = self._master_active_components()  # ← Both zapret and tg-ws-proxy
    # ...
    running_ids = {cid for cid in active_ids if states.get(cid) and states[cid].status == "running"}
    any_running = len(running_ids) > 0
    fully_running = bool(active_ids) and set(active_ids) == running_ids
    # ...
    self._set_badge("app", 
        self._t("Running") if fully_running 
        else (self._t("Partial") if any_running  # ← SHOWS "PARTIAL" HERE
        else self._t("Idle")), 
        # ...
    )
```

#### **File: `src/zapret_zen/services/components.py:496-561`**
```python
def _start_zapret(self, component_id: str) -> ComponentState:
    # Always restart to avoid conflicts
    self.stop_component(component_id)  # ← Takes time
    # ... preparation (1-2 seconds)
    process = subprocess.Popen(winws_command, ...)
    running = False
    for _ in range(24):  # ← POLLING LOOP: up to 6 seconds!
        if self._is_image_running("winws.exe"):
            running = True
            break
        time.sleep(0.25)  # ← 24 * 250ms = 6 seconds max
```

---

### 3. Why Manual Stop/Start Always Works

**When user clicks the power button:**

1. `_toggle_master_runtime()` is called (main_window.py:9531)
2. Sets `_toggle_in_progress = True` (line 9539)
3. Starts components in background worker (line 9548)
4. **Waits for completion** via `_ui_signals.toggle_done.emit()` (backend_worker.py:9564)
5. Only then calls `_on_master_toggle_finished()` which:
   - Sets `_toggle_in_progress = False`
   - Calls `refresh_all()` **AFTER** components are fully started

**Key Difference:** Manual start **blocks UI updates** (`_toggle_in_progress=True`) and only refreshes **after** startup completes.

---

### 4. Why It's Intermittent

The bug depends on **component startup speed:**

- **Fast startup (< 1.8s):** zapret finishes before T=1800ms refresh → No bug
- **Slow startup (> 1.8s):** zapret still starting at T=1800ms → Bug appears
- **Very slow (> 6s):** Both components not started → Shows "Idle" correctly

Factors affecting speed:
- System load
- Antivirus scanning
- Disk I/O
- Whether WinDivert driver is already loaded
- Whether previous winws.exe processes exist (requires cleanup)

---

## The Fix

### **Option 1: Delay UI Refresh Until Components Start (Recommended)**

**File: `src/zapret_zen/app.py:332-356`**

Change the autostart callback to signal UI when startup completes:

```python
if known.autostart_launch and settings.auto_run_components:
    def _start_after_backend() -> None:
        if context.backend is not None:
            # Set a flag to prevent premature UI refresh
            window.set_autostart_in_progress(True)
            
            def _on_autostart_complete(result):
                window.set_autostart_in_progress(False)
                window.refresh_all()
            
            window.start_enabled_components_async(
                autostart_only=True,
                on_complete=_on_autostart_complete
            )
    autostart_callback = _start_after_backend
```

**File: `src/zapret_zen/ui/main_window.py`**

Add to class:
```python
self._autostart_in_progress = False

def set_autostart_in_progress(self, value: bool) -> None:
    self._autostart_in_progress = value
```

Modify `refresh_dashboard()` at line 10991:
```python
def refresh_dashboard(self) -> None:
    # ... existing checks ...
    if not self._startup_snapshot_ready:
        self._ensure_local_runtime_snapshot()
    
    # NEW: Don't refresh during autostart - components are still starting
    if self._autostart_in_progress:
        self.power_button.setEnabled(False)
        self.power_button.setProperty("state", "loading")
        self._update_power_icon()
        if isinstance(self.power_button, AnimatedPowerButton):
            self.power_button.set_loading_state(True, animate=not self._page_transition_running)
        if self.power_aura is not None:
            self.power_aura.set_idle_pulse_enabled(False)
            self.power_aura.set_status_glow_enabled(True)
        self._set_badge("app", self._t("Starting"), "status_warn.svg")
        self._set_badge("zapret", self._t("Starting"), "status_warn.svg")
        self._set_badge("tg", self._t("Starting"), "status_warn.svg")
        self._set_badge("mods", self._t("Loading"), "status_mod.svg")
        return
    
    # ... rest of existing code ...
```

---

### **Option 2: Don't Show "Partial" During Initial Startup (Simpler)**

**File: `src/zapret_zen/ui/main_window.py:11032`**

Add startup grace period check:

```python
# At class init:
self._app_startup_time = time.time()

# In refresh_dashboard():
startup_grace_period = (time.time() - self._app_startup_time) < 10.0  # 10 seconds after app start

self._set_badge("app", 
    self._t("Running") if fully_running 
    else (self._t("Starting") if startup_grace_period and any_running  # ← Show "Starting" not "Partial"
    else (self._t("Partial") if any_running 
    else self._t("Idle"))), 
    "status_ok.svg" if fully_running 
    else ("status_warn.svg" if (any_running and not startup_grace_period)
    else "status_off.svg")
)
```

---

### **Option 3: Fix Component State Reading (Most Robust)**

The real issue is that `_component_states()` returns stale cached states.

**File: `src/zapret_zen/services/components.py:265-287`**

Problem: Cache lasts 700ms, but during startup, states change rapidly.

```python
def list_states(self) -> list[ComponentState]:
    # ISSUE: During startup, cache prevents seeing real-time state changes
    if self._state_cache and (time.time() - self._state_cache_at) < 0.7:
        return [...]  # ← Returns stale state during startup
    
    states = self._compute_states()  # ← This checks actual process status
    # ...
```

**Fix:** Invalidate cache after autostart completes.

**File: `src/zapret_zen/services/backend_worker.py:369-384`**

```python
@_register_action("start_enabled_components")
def _handle_start_enabled_components(context, payload, emit_progress):
    _sync_telegram_component_from_services(context)
    _sync_dns_manager_component_from_services(context)
    autostart_only = bool(payload.get("autostart_only", False)) if isinstance(payload, dict) else False
    components = context.processes.list_components()
    if autostart_only:
        for component in components:
            if component.enabled and component.autostart:
                context.processes.start_component(component.id)
    else:
        for component in components:
            if component.enabled:
                context.processes.start_component(component.id)
    
    # NEW: Force fresh state computation after all components started
    context.processes._invalidate_state_cache()  # ← Add this
    time.sleep(0.5)  # ← Give processes time to fully initialize
    context.processes._invalidate_state_cache()  # ← Invalidate again
    
    result = _snapshot(context)
    _attach_telegram_proxy_info(context, result)
    return result
```

---

## Recommended Solution

**Combine Option 1 + Option 3:**

1. Add `_autostart_in_progress` flag to prevent UI from showing partial state during autostart
2. Invalidate state cache after autostart completes to ensure fresh data
3. Explicitly refresh UI only after backend confirms all components started

This matches the behavior of manual start/stop, which is why manual restart always works.

---

## Testing Steps

After applying the fix:

1. **Test cold start after PC reboot** - should show "Starting" → "Running", never "Partial"
2. **Test normal restart** - same behavior
3. **Test with slow disk/high CPU** - should wait for completion
4. **Test with only zapret enabled** - should show "Running" when ready
5. **Test with only tg-ws-proxy enabled** - should show "Running" when ready
6. **Test manual stop/start** - should continue to work as before

---

## Files to Modify

1. `src/zapret_zen/app.py` - Add completion callback to autostart
2. `src/zapret_zen/ui/main_window.py` - Add `_autostart_in_progress` flag and guard
3. `src/zapret_zen/services/backend_worker.py` - Invalidate cache after startup
4. `src/zapret_zen/services/components.py` - (Optional) Add `force_refresh_states()` method

---

**Report prepared:** 2026-06-24  
**Bug severity:** Medium (UI inconsistency, not functional failure)  
**Fix complexity:** Low-Medium (targeted changes, no architecture refactor needed)
