from pydantic import BaseModel
from binance_square_bot.services.base import BaseSource, BaseTarget

def test_base_source_config():
    """Test BaseSource has default config."""
    assert BaseSource.Config.model_fields["enabled"].default is True
    assert BaseSource.Config.model_fields["daily_max_executions"].default == 1

def test_base_target_config():
    """Test BaseTarget has default config."""
    assert BaseTarget.Config.model_fields["enabled"].default is True
    assert BaseTarget.Config.model_fields["daily_max_posts_per_key"].default == 100
    assert BaseTarget.Config.model_fields["api_keys"].default == []

def test_subclass_inheritance():
    """Test subclass can inherit and extend config."""
    class TestModel(BaseModel):
        name: str

    class TestSource(BaseSource):
        Model = TestModel

        class Config(BaseSource.Config):
            custom_field: str = "test"

        def fetch(self):
            return TestModel(name="test")

        def generate(self, data):
            return data.name

    # Config should have both inherited and custom fields
    assert "enabled" in TestSource.Config.model_fields
    assert "daily_max_executions" in TestSource.Config.model_fields
    assert "custom_field" in TestSource.Config.model_fields
    assert TestSource.Config.model_fields["custom_field"].default == "test"

    # Model should be registered
    assert TestSource.Model == TestModel

def test_target_filter_default():
    """Test default filter passes through content."""
    class TestTarget(BaseTarget):
        def publish(self, content, api_key):
            return (True, "")

    target = TestTarget()
    assert target.filter("test content") == "test content"
