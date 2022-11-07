#############################################################################
# Copyright (c), Jupyter Development Team                                   #                                         #
#                                                                           #
# Distributed under the terms of the BSD 3-Clause License.                  #
#                                                                           #
# The full license is in the file LICENSE, distributed with this software.  #
#############################################################################

import json
import re
from pathlib import Path

import click
from jupyter_releaser.util import get_version, run
from pkg_resources import parse_version

TBUMP_CMD = "tbump --non-interactive --only-patch"

JS_VERSION_PATTERN = "(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)(-(?P<channel>alpha|beta|rc)\\.(?P<release>\\d+))?"


@click.command()
@click.argument("spec", nargs=1)
def bump(spec):
    status = run("git status --porcelain").strip()
    if len(status) > 0:
        raise Exception("Must be in a clean git state with no untracked files")

    ###################################################################
    #                      Bump python version                        #
    ###################################################################
    curr = parse_version(get_version())
    version = spec
    if spec == "next":
        version = f"{curr.major}.{curr.minor}."
        if curr.pre:
            p, x = curr.pre
            version += f"{curr.micro}{p}{x + 1}"
        else:
            version += f"{curr.micro + 1}"

    elif spec == "patch":
        version = f"{curr.major}.{curr.minor}.{curr.micro + 1}"

    elif spec == "minor":
        version = f"{curr.major}.{curr.minor + 1}.0"

    elif spec == "major":
        version = f"{curr.major + 1}.0.0"

    version = parse_version(version)

    # bump the Python package
    python_cmd = f"{TBUMP_CMD} {version}"
    run(python_cmd)

    ###################################################################
    #                        Bump JS version                          #
    ###################################################################
    HERE = Path(__file__).parent.parent.resolve()
    file_path = HERE / "javascript" / "package.json"
    with file_path.open() as f:
        data = json.load(f)

    if not data:
        raise Exception("File package.json not found")

    curr = get_js_version(data["version"])
    js_version = spec
    if spec == "next":
        js_version = f"{curr['major']}.{curr['minor']}."
        if curr["pre"]:
            p, x = curr["pre"]
            js_version += f"{curr['micro']}-{p}.{x + 1}"
        else:
            js_version += f"{curr['micro'] + 1}"

    elif spec == "patch":
        js_version = f"{curr['major']}.{curr['minor']}.{curr['micro'] + 1}"

    elif spec == "minor":
        js_version = f"{curr['major']}.{curr['minor'] + 1}.0"

    elif spec == "major":
        js_version = f"{curr['major'] + 1}.0.0"

    else:
        # convert the Python version
        js_version = f"{version.major}.{version.minor}.{version.micro}"
        if version.pre:
            p, x = version.pre
            p = p.replace("a", "alpha").replace("b", "beta")
            js_version += f"-{p}.{x}"

    if not data:
        raise Exception("File package.json not found")

    # bump the JS packages
    data["version"] = js_version
    with file_path.open(mode="+w") as f:
        json.dump(data, f, indent=2)


def get_js_version(current):
    match = re.match(JS_VERSION_PATTERN, current, re.VERBOSE | re.IGNORECASE)
    version = dict(
        major=int(match["major"]) | 0,
        minor=int(match["minor"]) | 0,
        micro=int(match["patch"]) | 0,
        pre=None,
    )

    if match["channel"]:
        version["pre"] = (match["channel"], int(match["release"]))

    return version


if __name__ == "__main__":
    bump()
