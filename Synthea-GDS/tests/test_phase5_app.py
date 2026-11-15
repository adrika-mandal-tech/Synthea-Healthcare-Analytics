import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, relative_path: str):
    module_path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_validation_layer_imports():
    import graph_intelligence.validation as validation

    assert hasattr(validation, "extract_claims")
    assert hasattr(validation, "match_claims_to_evidence")
    assert hasattr(validation, "calculate_coverage")
    assert hasattr(validation, "detect_hallucinations")
    assert hasattr(validation, "generate_validation_report")


def test_streamlit_app_modules_exist():
    _load_module("synthea_streamlit_app", "graph_intelligence/app/streamlit_app.py")
    _load_module("synthea_overview_page", "graph_intelligence/app/pages/1_Overview.py")
    _load_module("synthea_copilot_page", "graph_intelligence/app/pages/2_Copilot.py")
    _load_module("synthea_community_page", "graph_intelligence/app/pages/3_Community.py")
    _load_module("synthea_entity_page", "graph_intelligence/app/pages/4_Entity.py")


def test_covid_aware_pages_render_dataset_context():
    import importlib.util
    import sys
    from pathlib import Path
    from types import SimpleNamespace

    root = Path(__file__).resolve().parents[1]

    class DummyStreamlit:
        def __init__(self):
            self.messages = []

        def title(self, *args, **kwargs):
            self.messages.append(("title", args[0]))

        def write(self, *args, **kwargs):
            self.messages.append(("write", args[0]))

        def info(self, *args, **kwargs):
            self.messages.append(("info", args[0]))

        def caption(self, *args, **kwargs):
            self.messages.append(("caption", args[0]))

        def text_area(self, *args, **kwargs):
            self.messages.append(("text_area", args[0]))
            return "Which entities are most central in the COVID-19 referral network?"

        def button(self, *args, **kwargs):
            self.messages.append(("button", args[0]))
            return True

        def success(self, *args, **kwargs):
            self.messages.append(("success", args[0]))

        def subheader(self, *args, **kwargs):
            self.messages.append(("subheader", args[0]))

        def dataframe(self, *args, **kwargs):
            self.messages.append(("dataframe", args[0]))

        def bar_chart(self, *args, **kwargs):
            self.messages.append(("bar_chart", args[0]))

        def json(self, *args, **kwargs):
            self.messages.append(("json", args[0]))

    stub = DummyStreamlit()
    sys.modules["streamlit"] = SimpleNamespace(**stub.__dict__)

    for page_name in ["2_Copilot.py", "5_Similarity.py", "6_Embeddings.py", "7_Anomalies.py", "8_Robustness.py"]:
        module_path = root / "graph_intelligence" / "app" / "pages" / page_name
        spec = importlib.util.spec_from_file_location(f"covid_page_{page_name}", module_path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        module.st = stub
        module.render()

    rendered = "\n".join(str(value) for _, value in stub.messages)
    assert "COVID-19" in rendered or "Synthea COVID-19" in rendered
