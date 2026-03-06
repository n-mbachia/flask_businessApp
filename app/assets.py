"""Utility helpers for building the Tailwind/PostCSS stylesheets."""
import os
import subprocess
import shutil

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
TAILWIND_INPUT = os.path.join(BASE_DIR, 'app', 'static', 'css', 'app.css')
TAILWIND_OUTPUT = os.path.join(BASE_DIR, 'app', 'static', 'css', 'styles.css')
TAILWIND_CONFIG = os.path.join(BASE_DIR, 'tailwind.config.js')


def _tailwind_sources():
    return [TAILWIND_INPUT, TAILWIND_CONFIG]


def _needs_tailwind_build(output_path: str, sources: list[str]) -> bool:
    if not os.path.exists(output_path):
        return True
    output_mtime = os.path.getmtime(output_path)
    for source in sources:
        if os.path.exists(source) and os.path.getmtime(source) > output_mtime:
            return True
    return False


def ensure_tailwind_built(force: bool = False) -> bool:
    
    """Build the Tailwind template when the stylesheet is missing or stale."""

    if os.environ.get('SKIP_TAILWIND_BUILD') == '1' and not force:
        print('Skipping Tailwind build (SKIP_TAILWIND_BUILD=1).')
        return False

    npm_executable = shutil.which('npm')
    if npm_executable is None:
        print('npm not found; install Node.js to build Tailwind assets.')
        return False

    if not os.path.exists(TAILWIND_INPUT):
        print(f'Tailwind input file missing: {TAILWIND_INPUT}')
        return False

    if not force and not _needs_tailwind_build(TAILWIND_OUTPUT, _tailwind_sources()):
        return False

    print('Compiling Tailwind CSS...')
    subprocess.run([npm_executable, 'run', 'tailwind:build'], cwd=BASE_DIR, check=True)
    return True
