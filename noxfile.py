from pathlib import Path
from textwrap import dedent

import nox
from nox_poetry import Session, session

package = "strawberry_graphql_mage"
python_versions = ["3.10", "3.9", "3.8"]
nox.needs_version = ">= 2021.10.1"
nox.options.sessions = (
    "pre-commit",
    "safety",
    "pyright",
    "markdownlint",
    "tests",
)
nox.options.reuse_existing_virtualenvs = True

requirements = Path("requirements.txt")


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

    hook_dir = Path(".git") / "hooks"
    if not hook_dir.is_dir():
        return

    for hook in hook_dir.iterdir():
        if hook.name.endswith(".sample") or not hook.is_file():
            continue

        text = hook.read_text()
        bin_dir = repr(session_.bin)[1:-1]  # strip quotes
        if not (Path("A") == Path("a") and bin_dir.lower() in text.lower() or bin_dir in text):
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


def _export_requirements(session_: Session):
    session_.run(
        "poetry",
        "export",
        f"-o{requirements}",
        "--dev",
        "--without-hashes",
        external=True,
    )


def install(session_, package_, version):
    if version == "latest":
        Session.install(session_, package, "-U")
    else:
        Session.install(session_, f"{package_}=={version}")


# noinspection PyUnresolvedReferences,PyProtectedMember
def export_requirements_without_extras(session_: Session) -> Path:
    """Ugly workaround to install only certain dev dependencies without extras"""
    extras = session_.poetry.poetry.config._config.get("extras", {})  # type: ignore
    session_.poetry.poetry.config._config["extras"] = {}  # type: ignore
    requirements = session_.poetry.export_requirements()
    session_.poetry.poetry.config._config["extras"] = extras  # type: ignore
    return requirements


def _cleanup_requirements():
    requirements.unlink()


def poetry_install(session_: Session):
    session_.install(f"-r{requirements}")


@session(name="pre-commit", python="3.10")
def pre_commit(session_: Session) -> None:
    """Lint using pre-commit."""
    args = session_.posargs or ["run", "--all-files", "--show-diff-on-failure"]
    session_.install(
        "darglint",
        "autopep8",
        "pep8-naming",
        "pre-commit",
        "pre-commit-hooks",
    )
    session_.run("pre-commit", *args)
    if args and args[0] == "install":
        activate_virtualenv_in_precommit_hooks(session_)


@session(python="3.10")
def safety(session_: Session) -> None:
    """Scan dependencies for insecure packages."""
    requirements = session_.poetry.export_requirements()
    session_.install("safety")
    session_.run("safety", "check", "--full-report", "--ignore=42194", f"--file={requirements}")


@session(python="3.10")
def pyright(session_: Session) -> None:
    """Type-check using mypy."""
    requirements = export_requirements_without_extras(session_)
    session_.install("-r", str(requirements))
    session_.run("pyright", external=True)
    if not session_.posargs:
        session_.run("pyright", "noxfile.py", external=True)


@session(python="3.10")
def markdownlint(session_: Session) -> None:
    """Check markdown files."""
    session_.run("markdownlint", "**/*.md", external=True)


@session(name="tests", python=python_versions)
def tests(session_: Session) -> None:
    """Run the test suite."""
    session_.install(".")
    requirements = export_requirements_without_extras(session_)
    session_.install("-r", str(requirements))

    try:
        session_.run("coverage", "run", "--parallel", "-m", "pytest", *session_.posargs)
    finally:
        if session_.interactive:
            session_.notify("coverage")


@session(python="3.10")
def coverage(session_: Session) -> None:
    """Produce the coverage report."""
    # Do not use session.posargs unless this is the only session.
    # noinspection PyProtectedMember
    session_count = len(session_._runner.manifest)
    has_args = session_.posargs and session_count == 1
    args = session_.posargs if has_args else ["report", "-i"]

    session_.install("coverage[toml]")

    if not has_args and any(Path().glob(".coverage.*")):
        session_.run("coverage", "combine")

    session_.run("coverage", *args)
