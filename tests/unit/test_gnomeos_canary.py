"""The baseline must reject substitute systems and accessibility fallbacks."""
from pathlib import Path

import pytest
import yaml

from tests.shared.gnomeos_canary import require_gnomeos_wayland

IDENTITY = 'ID=org.gnome.os\nNAME="GNOME OS"\nGNOMEOS_COMMIT=abc\nIMAGE_VERSION=nightly.1\n'
ENV = {
    "XDG_SESSION_TYPE": "wayland", "WAYLAND_DISPLAY": "wayland-0",
    "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1001/bus",
    "AT_SPI_BUS_ADDRESS": "unix:path=/run/user/1001/at-spi/bus",
}


def test_genuine_identity():
    assert require_gnomeos_wayland(IDENTITY, ENV)["NAME"] == "GNOME OS"


@pytest.mark.parametrize("key", ENV)
def test_missing_session_evidence_fails(key):
    env = ENV.copy()
    del env[key]
    with pytest.raises(AssertionError):
        require_gnomeos_wayland(IDENTITY, env)


@pytest.mark.parametrize("identity", ["", IDENTITY.replace("org.gnome.os", "dakota"),
                                    IDENTITY.replace("GNOMEOS_COMMIT=abc", "GNOMEOS_COMMIT="),
                                    IDENTITY.replace("IMAGE_VERSION=nightly.1", "IMAGE_VERSION=")])
def test_unknown_or_substitute_identity_fails(identity):
    with pytest.raises(AssertionError):
        require_gnomeos_wayland(identity, ENV)


def test_accessibility_fallback_fails():
    with pytest.raises(AssertionError, match="fallback"):
        require_gnomeos_wayland(IDENTITY, {**ENV, "AT_SPI_BUS_ADDRESS": ENV["DBUS_SESSION_BUS_ADDRESS"]})


def test_xorg_fails():
    with pytest.raises(AssertionError, match="Wayland"):
        require_gnomeos_wayland(IDENTITY, {**ENV, "XDG_SESSION_TYPE": "x11"})


def test_canary_caller_uses_strict_gate_and_preserves_evidence():
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/gnomeos-canary.yml").read_text())
    steps = workflow["jobs"]["canary"]["steps"]
    action_step = next(s for s in steps if s.get("uses", "").endswith("/gnome-e2e"))
    assert action_step["with"]["suite"] == "gnomeos-canary"
    action = yaml.safe_load((root / ".github/actions/gnome-e2e/action.yml").read_text())
    gate = next(s for s in action["runs"]["steps"] if s["name"] == "Gate extension-validation run")
    assert "always()" in gate["if"] and "inputs.suite == 'gnomeos-canary'" in gate["if"]
    upload = next(s for s in steps if s.get("uses", "").startswith("actions/upload-artifact@"))
    assert upload["if"] == "always()"
    assert "bootc-install.log" in upload["with"]["path"]
