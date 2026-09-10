# BetterDisplay Home Assistant integration

Custom `custom_components/betterdisplay` for Home Assistant, controlling display
brightness, power, volume, mute and input source via BetterDisplay's HTTP
integration API.

## Requirements

### What to enable in BetterDisplay

The HTTP server is **off by default** -- only CLI and notification integration
are enabled out of the box, so this step is required.

1. Open BetterDisplay > **Settings** (gear icon) > **Application** > **Integration**.
2. Under **HTTP integration**, turn on **"Enable integrated HTTP server"**
   ("Allows access to app functionality via HTTP requests").
3. **"Listening HTTP port"** sets the TCP port; the default is `55777`. Use the
   same value in the Home Assistant config flow.
4. Optionally set the integration token in that same pane. If you do, enter it
   during setup -- it is sent as the `token=` query parameter.

The server binds to all interfaces, so Home Assistant reaches it over the LAN
with no extra tunnel or broker. macOS may ask to allow incoming connections the
first time -- accept it.

Note that the HTTP interface itself, DDC brightness, DDC volume, DDC power and
DDC input switching are all **free** features of BetterDisplay -- a Pro license
is not required for anything this integration does. See
[List of free and Pro features](https://github.com/waydabber/BetterDisplay/wiki/List-of-free-and-Pro-features).

### On the Home Assistant side

- The Mac must be reachable from Home Assistant over the LAN.
- Which entities appear depends on what the display reports over DDC. Volume and
  mute entities are only created for displays with hardware volume control, and
  the input source picker only for displays that expose an input source list.
- Turning a display off uses BetterDisplay's `hardwareBacklight` command, which
  needs a display with DDC (or smart protocol) backlight support. Displays
  without it fall back to dimming to 0%.

## Installation

### HACS (custom repository)

1. HACS > three-dot menu > **Custom repositories**.
2. Repository `https://github.com/mzspicoli/ha-betterdisplay`, type
   **Integration**, then **Add**.
3. Find "BetterDisplay" in HACS, **Download**, then restart Home Assistant.
4. **Settings > Devices & services > Add integration > BetterDisplay**, and enter
   the Mac's IP and port.

### Manual

Copy `custom_components/betterdisplay/` into your Home Assistant `config/custom_components/`
directory and restart, then add the integration from the UI as above.

## Why this instead of the original MQTT bridge idea

Started from https://github.com/MonitorControl/MonitorControl/issues/1881, redirected
by the MonitorControl maintainer to BetterDisplay (same author, `waydabber`).
BetterDisplay's main GitHub repo is closed-source (README + issues only) so no code
PR is possible there -- but `betterdisplaycli` (https://github.com/waydabber/betterdisplaycli)
and BetterDisplay's HTTP integration API (`Settings > Application > Integration >
Enable integrated HTTP server`, default port 55777, see
https://github.com/waydabber/BetterDisplay/wiki/Integration-features,-CLI) are
public and support everything needed. Since BetterDisplay's HTTP server binds to
all interfaces (confirmed: `lsof` showed `*:55777`) and the app's firewall rule
allows incoming connections, Home Assistant can reach it directly over LAN with
plain HTTP -- no MQTT broker needed at all.

## What it does

One device per display, with up to four entities:

| Entity | BetterDisplay parameter | Notes |
| --- | --- | --- |
| `light.<display>` | `brightness`, `hardwareBacklight` | Brightness-only color mode. |
| `number.<display>_volume` | `volume` | 0-100%, only for displays with DDC volume. |
| `switch.<display>_mute` | `mute` | Only for displays with DDC volume. |
| `select.<display>_input_source` | `inputSourceList`, `changeInputSource` | Write-only, see below. |

- Config flow: host, port (default 55777), optional integration token.
- `DataUpdateCoordinator` polls `GET /get?identifiers` (display list) plus
  `brightness`, `hardwareBacklight`, `volume` and `mute` per display every 10s.
  The input source list is static, so it is read once per display.
- `light.turn_off` calls `GET /set?tagID=<id>&hardwareBacklight=off`, which cuts
  the panel's backlight over DDC so the monitor actually powers down. Setting
  brightness to 0 instead only renders a black screen on a still-lit display.
  Displays that don't report a `hardwareBacklight` value (the API answers
  `Failed.`) fall back to the old brightness-to-0 behaviour.

> [!WARNING]
> Switching the input source points the monitor at another device, so the Mac's
> picture disappears until something switches it back. DDC input source is
> write-only in practice (reading VCP `0x60` back fails on most Apple Silicon
> connections), so the `select` entity reports the last value *it* sent and stays
> `unknown` until then -- it cannot detect input changes made with the monitor's
> own buttons. The option list comes straight from BetterDisplay and covers every
> input DDC can address, not just the ports your monitor physically has.

## Bugs found and fixed during testing against real hardware

1. **Flag-style query params silently dropped.** BetterDisplay's API treats
   `?brightness` (bare) and `?brightness=` (empty value) as the same "get this
   value" flag -- confirmed via curl. My first `_params()` implementation
   filtered out `None`-valued kwargs entirely (used to mark flag params),
   producing requests with the parameter missing altogether, which the app
   correctly rejected (`cannot_connect` in the config flow, `Failed.` from the
   app). Fixed by encoding `None` as an empty string instead of dropping the key.
2. **Only `ATTR_BRIGHTNESS` handled in `async_turn_on`.** Home Assistant's
   frontend light controls can call `light.turn_on` with `brightness_pct`
   instead of `brightness` depending on the control. The entity only checked
   for `brightness`, so percentage-based calls silently fell through to a
   100%-default branch. Fixed by handling both.

## Test performed (2026-08-05)

Against the user's real Mac (BetterDisplay installed, one physical monitor,
`CU34V5C`) and real production Home Assistant instance (`home.picoli.eu`,
192.168.178.111), reached over LAN from 192.168.178.6:55777:

1. Verified BetterDisplay's HTTP API directly with curl: listed the real display,
   read/set brightness, confirmed the physical monitor's brightness actually
   changed and restored it afterwards.
2. Verified cross-host reachability by SSHing into the Home Assistant host itself
   (`192.168.178.111`) and curling the Mac's `55777` from there -- confirms the
   real integration environment (not just localhost) can reach BetterDisplay.
3. Installed the custom component into the live HA config (`custom_components/`),
   restarted HA, added the integration via the UI (`Settings > Devices & Services
   > Add Integration > BetterDisplay`, host `192.168.178.6`, port `55777`).
4. First attempt failed with `cannot_connect` -- root-caused to bug #1 above via
   direct curl comparison, fixed, redeployed, restarted, retried: integration
   set up successfully and auto-discovered the real display `CU34V5C`.
5. Called `light.turn_on` with explicit `brightness: 128` via the HA REST API --
   confirmed via BetterDisplay's HTTP API that the physical monitor's brightness
   actually changed to `0.502` (128/255).
6. Called `light.turn_on` with `brightness_pct: 70` -- initially had no effect
   (bug #2), root-caused, fixed, redeployed, restarted, retried: physical
   brightness changed to `0.698` (70%) as expected.
7. Restored the monitor to its original brightness (`0.934`) after each test.

## Known gaps

- Contrast (`hardwareContrast`) and the per-channel gain/black level parameters
  aren't exposed yet; they'd follow the same pattern as volume.
- No token auth tested end-to-end (field exists in config flow, untested against
  BetterDisplay's optional `token=` safeguard).
- Input source switching is implemented from the documented API but not verified
  against real hardware -- testing it means losing the picture on the test Mac.
- Only tested against one display (AOC CU34V5C) on one Mac. Reports from other
  hardware are welcome in the issue tracker.
- No `DeviceInfo.sw_version` niceties, no diagnostics, no tests.
- Installable as a HACS custom repository; not submitted to the HACS default
  list (that additionally needs a logo in `home-assistant/brands`).

## Files

`custom_components/betterdisplay/`: `__init__.py`, `api.py`, `config_flow.py`,
`const.py`, `coordinator.py`, `entity.py`, `light.py`, `number.py`, `select.py`,
`switch.py`, `manifest.json`, `strings.json`, `translations/`, `brand/`.
