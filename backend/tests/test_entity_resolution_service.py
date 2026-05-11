from app.services.entity_resolution import EntityResolutionService


def test_normalize_text():
    svc = EntityResolutionService()
    assert svc.normalize_text("  Foo   BAR ") == "foo bar"


def test_coerce_entity_type_unknown():
    svc = EntityResolutionService()
    from app.models import EntityType

    assert svc._coerce_entity_type("not_a_real_type") == EntityType.OTHER
