"""Entry point for ``python -m policyfoundry`` and the ``policyfoundry`` CLI.

Registered as ``policyfoundry.__main__:main`` in pyproject.toml
``[project.scripts]``.
"""

from policyfoundry.main import app


def main() -> None:
    """Run the PolicyFoundry CLI application."""
    app()


if __name__ == "__main__":
    main()
