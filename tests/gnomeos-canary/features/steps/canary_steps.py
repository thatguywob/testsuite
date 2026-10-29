"""Keep the GUI probe in a bounded child process; no fallback input paths."""
import os
from pathlib import Path
import subprocess
import sys

from behave import given, when, then

from tests.shared.gnomeos_canary import require_gnomeos_wayland


@given("the guest is a genuine GNOME OS Wayland desktop")
def genuine_guest(context):
    require_gnomeos_wayland(Path("/usr/lib/os-release").read_text(), os.environ)
    # Do not run untrusted extensions under the existing administrative harness.
    installed = subprocess.run(["gnome-extensions", "list"], check=True,
                               capture_output=True, text=True, timeout=15)
    assert not installed.stdout.strip(), "Baseline canary requires a guest without extensions"


@when("virtual input types into the canary window")
def input_canary(context):
    script = Path(__file__).resolve().parents[3] / "shared/gnomeos_canary.py"
    context.canary_result = subprocess.run(
        [sys.executable, str(script)], check=True, timeout=90,
    )


@then("accessibility reports the exact text and desktop evidence is saved")
def canary_evidence(context):
    import json
    results = Path("/tmp/gnome_e2e/results")
    data = json.loads((results / "desktop-canary.json").read_text())
    assert data["expected"] == data["observed"] and data["observed"]
    assert (results / "desktop-canary.png").stat().st_size > 0
