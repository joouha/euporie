"""Tests for the JsonFileLayer."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest

from euporie.core.config._layers import JsonFileLayer

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def json_path(tmp_path: Path) -> Path:
    """Return a path to a temporary JSON config file."""
    return tmp_path / "config.json"


def _make_setting(name: str, default: Any = None, schema: dict | None = None) -> Any:
    """Create a minimal mock setting for testing."""
    from types import SimpleNamespace

    return SimpleNamespace(
        name=name,
        default=default,
        schema=schema or {"type": "string"},
    )


class TestJsonFileLayerLoad:
    """Tests for JsonFileLayer.load."""

    def test_load_empty_when_file_missing(self, json_path: Path) -> None:
        """Test that loading from a missing file yields an empty layer."""
        layer = JsonFileLayer(json_path)
        settings = {"color": _make_setting("color")}
        layer.load(settings)
        assert dict(layer) == {}

    def test_load_global_values(self, json_path: Path) -> None:
        """Test loading top-level scalar values."""
        json_path.write_text(json.dumps({"color": "dark", "tabs": 4}))
        layer = JsonFileLayer(json_path)
        settings = {
            "color": _make_setting("color"),
            "tabs": _make_setting("tabs"),
        }
        layer.load(settings)
        assert layer["color"] == "dark"
        assert layer["tabs"] == 4

    def test_load_global_excludes_dicts(self, json_path: Path) -> None:
        """Test that nested dicts are excluded from global values."""
        json_path.write_text(json.dumps({"color": "dark", "notebook": {"tabs": 4}}))
        layer = JsonFileLayer(json_path)
        settings = {"color": _make_setting("color")}
        layer.load(settings)
        assert "notebook" not in layer
        assert layer["color"] == "dark"

    def test_load_namespaced_values(self, json_path: Path) -> None:
        """Test loading values from a namespace section."""
        json_path.write_text(json.dumps({"notebook": {"tabs": 4, "color": "light"}}))
        layer = JsonFileLayer(json_path, namespace="notebook")
        settings = {
            "tabs": _make_setting("tabs"),
            "color": _make_setting("color"),
        }
        layer.load(settings)
        assert layer["tabs"] == 4
        assert layer["color"] == "light"

    def test_load_invalid_json(self, json_path: Path) -> None:
        """Test that invalid JSON results in an empty layer."""
        json_path.write_text("{invalid json")
        layer = JsonFileLayer(json_path)
        settings = {"color": _make_setting("color")}
        layer.load(settings)
        assert dict(layer) == {}

    def test_load_non_object_json(self, json_path: Path) -> None:
        """Test that a non-object JSON root results in an empty layer."""
        json_path.write_text(json.dumps([1, 2, 3]))
        layer = JsonFileLayer(json_path)
        settings = {"color": _make_setting("color")}
        layer.load(settings)
        assert dict(layer) == {}


class TestJsonFileLayerSave:
    """Tests for JsonFileLayer.save."""

    def test_save_raises_when_not_persistable(self, json_path: Path) -> None:
        """Test that save raises NotImplementedError when not persistable."""
        layer = JsonFileLayer(json_path, persistable=False)
        with pytest.raises(NotImplementedError):
            layer.save("color", "dark")

    def test_save_global_value(self, json_path: Path) -> None:
        """Test saving a global value."""
        layer = JsonFileLayer(json_path, persistable=True)
        layer.save("color", "dark")
        data = json.loads(json_path.read_text())
        assert data["color"] == "dark"

    def test_save_namespaced_value(self, json_path: Path) -> None:
        """Test saving a namespaced value."""
        layer = JsonFileLayer(json_path, namespace="notebook", persistable=True)
        layer.save("tabs", 4)
        data = json.loads(json_path.read_text())
        assert data["notebook"]["tabs"] == 4

    def test_save_none_stores_null_global(self, json_path: Path) -> None:
        """Test that saving None stores null in JSON."""
        json_path.write_text(json.dumps({"color": "dark"}))
        layer = JsonFileLayer(json_path, persistable=True)
        layer.save("color", None)
        data = json.loads(json_path.read_text())
        assert "color" in data
        assert data["color"] is None

    def test_save_none_stores_null_namespaced(self, json_path: Path) -> None:
        """Test that saving None stores null in a namespace."""
        json_path.write_text(json.dumps({"notebook": {"color": "dark", "tabs": 4}}))
        layer = JsonFileLayer(json_path, namespace="notebook", persistable=True)
        layer.save("color", None)
        data = json.loads(json_path.read_text())
        assert data["notebook"]["color"] is None
        assert data["notebook"]["tabs"] == 4

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Test that save creates parent directories."""
        json_path = tmp_path / "subdir" / "nested" / "config.json"
        layer = JsonFileLayer(json_path, persistable=True)
        layer.save("color", "dark")
        assert json_path.exists()
        data = json.loads(json_path.read_text())
        assert data["color"] == "dark"

    def test_save_preserves_existing_values(self, json_path: Path) -> None:
        """Test that saving preserves other existing values."""
        json_path.write_text(json.dumps({"color": "dark", "tabs": 4}))
        layer = JsonFileLayer(json_path, persistable=True)
        layer.save("font", "mono")
        data = json.loads(json_path.read_text())
        assert data == {"color": "dark", "tabs": 4, "font": "mono"}


class TestJsonFileLayerSerialization:
    """Tests for JsonFileLayer value serialization."""

    def test_save_path_as_string(self, json_path: Path, tmp_path: Path) -> None:
        """Test that Path objects are serialized as strings."""
        output_path = tmp_path / "output.txt"
        layer = JsonFileLayer(json_path, persistable=True)
        layer.save("output", output_path)
        data = json.loads(json_path.read_text())
        assert data["output"] == str(output_path)
        assert isinstance(data["output"], str)

    def test_save_nested_list(self, json_path: Path) -> None:
        """Test that lists are serialized correctly."""
        layer = JsonFileLayer(json_path, persistable=True)
        layer.save("items", ["a", "b", "c"])
        data = json.loads(json_path.read_text())
        assert data["items"] == ["a", "b", "c"]

    def test_save_nested_dict(self, json_path: Path) -> None:
        """Test that nested dicts are serialized correctly."""
        layer = JsonFileLayer(json_path, persistable=True)
        layer.save("options", {"x": 1, "y": 2})
        data = json.loads(json_path.read_text())
        assert data["options"] == {"x": 1, "y": 2}


class TestJsonFileLayerPersistable:
    """Tests for the persistable property."""

    def test_not_persistable_by_default(self, json_path: Path) -> None:
        """Test that layers are not persistable by default."""
        layer = JsonFileLayer(json_path)
        assert layer.persistable is False

    def test_persistable_when_set(self, json_path: Path) -> None:
        """Test that layers are persistable when configured."""
        layer = JsonFileLayer(json_path, persistable=True)
        assert layer.persistable is True
