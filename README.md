# BetterDisplay Home Assistant integration (proof of concept)

Custom `custom_components/betterdisplay` for Home Assistant, exposing BetterDisplay
display brightness as a `light` entity via BetterDisplay's HTTP integration API.

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

- `light.<display>` entity per connected display, brightness-only (`ColorMode.BRIGHTNESS`).
- Config flow: host, port (default 55777), optional integration token.
- `DataUpdateCoordinator` polls `GET /get?identifiers` (display list),
  `GET /get?tagID=<id>&brightness` and `GET /get?tagID=<id>&hardwareBacklight`
  every 10s.
- `light.turn_on` (with `brightness` or `brightness_pct`) calls
  `GET /set?tagID=<id>&brightness=<0-1>`.
- `light.turn_off` calls `GET /set?tagID=<id>&hardwareBacklight=off`, which cuts
  the panel's backlight over DDC so the monitor actually powers down. Setting
  brightness to 0 instead only renders a black screen on a still-lit display.
  Displays that don't report a `hardwareBacklight` value (the API answers
  `Failed.`) fall back to the old brightness-to-0 behaviour.

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

## Known gaps before this is publish-ready

- Only brightness is exposed; contrast/volume/input could follow the same
  pattern using BetterDisplay's `hardwareContrast`, `volume`, `changeInputSource`
  parameters (probably as `number`/`select` entities).
- No token auth tested end-to-end (field exists in config flow, untested against
  BetterDisplay's optional `token=` safeguard).
- No `DeviceInfo.sw_version`/`manufacturer` niceties, no diagnostics, no tests.
- Not yet submitted anywhere -- this is a local proof of concept.

## Files

`custom_components/betterdisplay/`: `__init__.py`, `api.py`, `config_flow.py`,
`const.py`, `coordinator.py`, `light.py`, `manifest.json`, `strings.json`.
