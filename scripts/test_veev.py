"""
veev.to extractor probe — delegates to the generic provider test script.

Usage:
    python scripts/test_veev.py [embed_url]

Default test URL:
    https://veev.to/e/27kYAOe9AbsIceAnuwJ36B2xKnlZdIfwhFzjjJc?rback=1
"""

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TEST_URL = "https://veev.to/e/27kYAOe9AbsIceAnuwJ36B2xKnlZdIfwhFzjjJc?rback=1"

if len(sys.argv) < 2:
    sys.argv.append(TEST_URL)

# Re-use the generic provider probe (test_voe_custom_domain.py)
import importlib.util, pathlib

spec = importlib.util.spec_from_file_location(
    "provider_probe",
    pathlib.Path(__file__).parent / "test_voe_custom_domain.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.main()
