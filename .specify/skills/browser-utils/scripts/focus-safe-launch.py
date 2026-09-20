#!/usr/bin/env python3
"""Resolve the focus-safe browser launch rung for browser-utils (Tier 2).

Choosing how to launch a browser so its window never contends for the user's system
focus is deterministic environment probing plus two judgment inputs. The probing
belongs here; the judgment stays with the caller.

The ladder and its rationale are owned by ../references/focus-safe-launch.md — this
script implements that ladder, it does not redefine it.

Usage
-----
    focus-safe-launch.py [--headed-required BOOL] [--desktop-window BOOL]
                         [--screen WxHxD] [--cmd CMD] [--json]

    --headed-required   Does the task genuinely need headed rendering fidelity?
                        (false = F0 headless; the default)
    --desktop-window    Did the user explicitly ask to watch the run live on their
                        own desktop? Never infer this — it is the only path to F2.
    --screen            Virtual-display geometry for F1 (default 1440x900x24).
    --cmd               Command to wrap; makes the emitted wrapper directly runnable.
    --json              Machine-readable output (default is a human-readable report).

Exit codes
----------
    0   a rung was resolved (F0, F1, or F2)
    3   blocked — headed-on-desktop was requested but no display exists
    2   usage error
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shlex
import shutil
import sys

LADDER_REF = "references/focus-safe-launch.md"

# F2 keeps the window small and fixed; --start-maximized/--start-fullscreen/--kiosk
# claim the whole screen and are never passed. See the owner doc § F2.
F2_ARGS = ["--window-size=1280,800", "--window-position=64,64"]


def _bool(text: str) -> bool:
    low = text.strip().lower()
    if low in {"1", "true", "yes", "y", "on"}:
        return True
    if low in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"expected a boolean, got {text!r}")


def probe_environment() -> dict:
    """First-hand environment facts. Probed, never assumed."""
    system = platform.system()
    display = os.environ.get("DISPLAY") or ""
    wayland = os.environ.get("WAYLAND_DISPLAY") or ""
    return {
        "os": system,
        "display": display or None,
        "waylandDisplay": wayland or None,
        "hasDisplay": bool(display or wayland),
        "sessionType": os.environ.get("XDG_SESSION_TYPE") or None,
        "xvfbRun": shutil.which("xvfb-run"),
        "xdotool": shutil.which("xdotool"),
        "wmctrl": shutil.which("wmctrl"),
    }


def resolve(env: dict, headed_required: bool, desktop_window: bool, screen: str, cmd: str | None) -> dict:
    system = env["os"]
    xvfb = env["xvfbRun"]

    def result(rung, reason, headless, args=None, wrapper="", announce=False, degraded=False, blocked=False, hint=None):
        return {
            "rung": rung,
            "reason": reason,
            "headless": headless,
            "playwrightOptions": {"headless": headless, **({"args": args} if args else {})},
            "wrapper": wrapper,
            "announceFirst": announce,
            "focusRisk": "impossible" if rung in {"F0", "F1"} else ("best-effort" if rung == "F2" else "unresolved"),
            "degradedFidelity": degraded,
            "blocked": blocked,
            "hint": hint,
            "ladderRef": LADDER_REF,
        }

    # Rung F0 — no headed fidelity required. Structurally zero focus risk.
    if not headed_required:
        return result(
            "F0",
            "Task does not require headed rendering fidelity; headless has structurally zero focus risk.",
            headless=True,
        )

    # Headed fidelity required. F2 only on an explicit user request to watch.
    if desktop_window:
        if not env["hasDisplay"]:
            return result(
                "BLOCKED",
                "F2 (headed on the user's desktop) was requested but no display exists on this host.",
                headless=False,
                blocked=True,
                hint=(
                    "There is no DISPLAY/WAYLAND_DISPLAY, so a headed browser cannot start at all "
                    "(it aborts with 'Missing X server or $DISPLAY'). Re-run with --headed-required false "
                    "for F0, or install xvfb for F1."
                ),
            )
        wrapper = ""
        if cmd:
            wrapper = cmd
        return result(
            "F2",
            "User explicitly asked to watch the run on their own desktop; a real window will appear.",
            headless=False,
            args=list(F2_ARGS),
            wrapper=wrapper,
            announce=True,
            hint=(
                "Announce the window before launching. No Chromium switch guarantees non-activation — "
                "the window manager decides, so the window may still take focus once. Never call "
                "page.bringToFront(); capture is CDP-based and needs no focus."
            ),
        )

    # Headed fidelity required, but not on the user's desktop → F1 if the host can do it.
    if system == "Linux" and xvfb:
        wrapper = f'xvfb-run -a --server-args="-screen 0 {screen}"'
        if cmd:
            wrapper = f"{wrapper} bash -lc {shlex.quote(cmd)}"
        return result(
            "F1",
            "Headed rendering fidelity is required; a virtual display gives it with zero desktop presence.",
            headless=False,
            wrapper=wrapper,
            hint="Requires the xvfb package. Screenshots are identical to F0 — capture never needs a real screen.",
        )

    # F1 unavailable: no bundled virtual-display equivalent outside Linux X11.
    missing = "xvfb-run is not installed" if system == "Linux" else f"{system} has no bundled virtual-display equivalent"
    installs = {
        "Linux": "sudo apt-get install xvfb  (Debian/Ubuntu) | sudo dnf install xorg-x11-server-Xvfb  (RHEL/Fedora)",
    }
    return result(
        "F0",
        f"Headed fidelity was requested but F1 is unavailable ({missing}); falling back to headless rather than intruding on the desktop.",
        headless=True,
        degraded=True,
        hint=(
            "Fidelity is degraded relative to the request. To get F1, install a virtual display: "
            f"{installs.get(system, 'no packaged recipe — use F0 or an explicit F2')}. "
            "Otherwise accept F0, or re-run with --desktop-window true for an announced F2."
        ),
    )


def render_human(res: dict, env: dict) -> str:
    lines = [
        f"rung        {res['rung']}",
        f"reason      {res['reason']}",
        f"focusRisk   {res['focusRisk']}",
        f"headless    {str(res['headless']).lower()}",
        f"options     {json.dumps(res['playwrightOptions'], ensure_ascii=False)}",
    ]
    if res["wrapper"]:
        lines.append(f"wrapper     {res['wrapper']}")
    if res["announceFirst"]:
        lines.append("announce    YES — tell the user a window will appear on their desktop before launching")
    if res["degradedFidelity"]:
        lines.append("degraded    YES — headed fidelity could not be provided")
    if res["hint"]:
        lines.append(f"hint        {res['hint']}")
    lines.append(
        "env         os={os} display={display} wayland={wayland} xvfb-run={xvfb} xdotool={xdotool} wmctrl={wmctrl}".format(
            os=env["os"],
            display=env["display"] or "-",
            wayland=env["waylandDisplay"] or "-",
            xvfb="yes" if env["xvfbRun"] else "no",
            xdotool="yes" if env["xdotool"] else "no",
            wmctrl="yes" if env["wmctrl"] else "no",
        )
    )
    lines.append(f"ladder      {LADDER_REF}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="focus-safe-launch.py",
        description="Resolve the focus-safe browser launch rung (F0 headless / F1 virtual display / F2 announced desktop window).",
        epilog=f"Ladder owner: {LADDER_REF}",
    )
    parser.add_argument("--headed-required", type=_bool, nargs="?", const=True, default=False,
                        help="task genuinely needs headed rendering fidelity (default: false)")
    parser.add_argument("--desktop-window", type=_bool, nargs="?", const=True, default=False,
                        help="user explicitly asked to watch on their own desktop (default: false)")
    parser.add_argument("--screen", default="1440x900x24", help="F1 virtual-display geometry (default: %(default)s)")
    parser.add_argument("--cmd", default=None, help="command to wrap, making the wrapper directly runnable")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args(argv)

    env = probe_environment()
    res = resolve(env, args.headed_required, args.desktop_window, args.screen, args.cmd)

    if args.json:
        print(json.dumps({"environment": env, "resolution": res}, indent=2, ensure_ascii=False))
    else:
        print(render_human(res, env))

    return 3 if res["blocked"] else 0


if __name__ == "__main__":
    sys.exit(main())
