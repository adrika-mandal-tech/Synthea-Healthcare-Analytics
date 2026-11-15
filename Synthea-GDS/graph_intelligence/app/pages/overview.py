import importlib.util
from pathlib import Path


def render():
    page_file = Path(__file__).with_name("1_Overview.py")
    spec = importlib.util.spec_from_file_location("synthea_overview_page", page_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load page file: {page_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.render()
