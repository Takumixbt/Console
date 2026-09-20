"""Hermes plugin root.

Hermes loads this file as ``hermes_plugins.console`` via
``spec_from_file_location`` and treats the repository directory as the
package path, so ``console/`` is imported as a submodule.
"""

from .console.hermes_plugin import register

__all__ = ["register"]
