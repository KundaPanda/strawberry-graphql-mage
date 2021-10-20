import sys
from pathlib import Path
from textwrap import dedent

import nox
from nox import Session
from nox import session

package = "strawberry_graphql_mage"
python_versions = ["3.10", "3.9", "3.8"]
nox.needs_version = ">= 2021.10.1"
nox.options.sessions = (
    "pre-commit",
    "safety",
    "mypy",
    "tests",
    "coverage",
)
nox.options.reuse_existing_virtualenvs = True


def activate_virtualenv_in_precommit_hooks(session_: Session) -> None:
    """Activate virtualenv in hooks installed by pre-commit.
    This function patches git hooks installed by pre-commit to activate the
    session's virtual environment. This allows pre-commit to locate hooks in
    that environment when invoked from git.
    Args:
        session_: The Session object.
    """
    if session_.bin is None:
        return

    virtualenv = session_.env.get("VIRTUAL_ENV")
    if virtualenv is None:
        return

    hookdir = Path(".git") / "hooks"
    if not hookdir.is_dir():
        return

    for hook in hookdir.iterdir():
        if hook.name.endswith(".sample") or not hook.is_file():
            continue

        text = hook.read_text()
        bindir = repr(session_.bin)[1:-1]  # strip quotes
        if not (
                Path("A") == Path("a") and bindir.lower() in text.lower() or bindir in text
        ):
            continue

        lines = text.splitlines()
        if not (lines[0].startswith("#!") and "python" in lines[0].lower()):
            continue

        header = dedent(
            f"""\
            import os
            os.environ["VIRTUAL_ENV"] = {virtualenv!r}
            os.environ["PATH"] = os.pathsep.join((
                {session_.bin!r},
                os.environ.get("PATH", ""),
            ))
            """
        )

        lines.insert(1, header)
        hook.write_text("\n".join(lines))


def poetry_install(session_: Session, requirements: Path):
    session_.run(
        "poetry",
        "export",
        f"-o{requirements}",
        "--dev",
        "--without-hashes",
        external=True,
    )
    session_.install(f"-r{requirements}")


@session(name="pre-commit", python="3.10")
def pre_commit(session_: Session) -> None:
    """Lint using pre-commit."""
    args = session_.posargs or ["run", "--all-files", "--show-diff-on-failure"]
    session_.install("pre-commit", )
    session_.run("pre-commit", *args)
    if args and args[0] == "install":
        activate_virtualenv_in_precommit_hooks(session_)


@session(python="3.10")
def safety(session_: Session) -> None:
    """Scan dependencies for insecure packages."""
    requirements = Path("requirements.txt")
    poetry_install(session_, requirements)
    session_.run("safety", "check", "--full-report", f"--file={requirements}")
    requirements.unlink()


@session(python="3.10")
def mypy(session_: Session) -> None:
    """Type-check using mypy."""
    args = session_.posargs or ["strawberry_mage"]
    requirements = Path("requirements.txt")
    poetry_install(session_, requirements)
    session_.run("mypy", *args)
    if not session_.posargs:
        session_.run("mypy", f"--python-executable={sys.executable}", "noxfile.py")
    requirements.unlink()


@session(name="tests", python=python_versions)
def tests(session_: Session) -> None:
    """Run the test suite."""
    requirements = Path("requirements.txt")
    poetry_install(session_, requirements)
    try:
        session_.run("python", "-m", "pytest", "--cov")
    finally:
        if session_.interactive:
            session_.notify("coverage")
    requirements.unlink()


@session(python="3.10")
def coverage(session_: Session) -> None:
    """Produce the coverage report."""
    # Do not use session.posargs unless this is the only session.
    nsessions = len(session_._runner.manifest)
    has_args = session_.posargs and nsessions == 1
    args = session_.posargs if has_args else ["report", "-i"]

    session_.install("coverage[toml]")

    if not has_args and any(Path().glob(".coverage.*")):
        session_.run("coverage", "combine")

    session_.run("coverage", *args)
