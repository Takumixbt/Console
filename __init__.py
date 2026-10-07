"""Hermes plugin root.

Hermes loads this file as ``hermes_plugins.console`` and treats the repository
folder as the package, so the ``console/`` directory is a submodule and every
import inside it is relative.
"""

from .console.hermes_plugin import register

__all__ = ["register"]
