import importlib
import pkgutil

from .. import modules


def load_all_models() -> None:
    importlib.import_module("app.models")
    for module in pkgutil.walk_packages(modules.__path__, prefix=f"{modules.__name__}."):
        if module.name.endswith(".infrastructure.models"):
            importlib.import_module(module.name)
