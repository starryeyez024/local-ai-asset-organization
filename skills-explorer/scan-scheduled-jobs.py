#!/usr/bin/env python3
"""List local launchd and cron definitions that directly name a script file.

Read-only. The result is a snapshot of job definitions, not proof that a job is
loaded, enabled at runtime, or has run successfully. Commands are never run.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

GENERATOR = Path(__file__).with_name("generate-scripts-json.py")
spec = importlib.util.spec_from_file_location("script_explorer_generator", GENERATOR)
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--launchd-dir", action="append", type=Path,
                        help="Override the default launchd directories; repeat to scan more than one")
    parser.add_argument("--cron-file", action="append", type=Path,
                        help="Override the default system cron files; repeat for more than one")
    args = parser.parse_args()
    warnings = []
    jobs = generator.observed_jobs(Path.home(), args.launchd_dir, cron_files=args.cron_file,
                                   warnings=warnings)
    output = [{**{key: job[key] for key in ("kind", "label", "schedule", "definition")},
               "scriptFiles": sorted(str(path) for path in job["paths"])} for job in jobs]
    print(json.dumps({"jobs": output, "scanWarnings": warnings}, indent=2))


if __name__ == "__main__":
    main()
