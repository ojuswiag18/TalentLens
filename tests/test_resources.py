from src.resource_recommender import get_resources, search_resources


def test_get_resources_known_skill():
    resources = get_resources("Power BI")
    assert len(resources) >= 3
    assert resources[0]["resource_type"] == "Documentation"


def test_get_resources_case_insensitive():
    assert get_resources("power bi") == get_resources("Power BI")


def test_get_resources_fallback():
    resources = get_resources("Quantum Weaving 9000")
    assert len(resources) >= 3
    assert all("Quantum Weaving 9000" in r["title"] for r in resources)


def test_resource_types_valid():
    valid = {"Documentation", "Course", "Article", "Video", "Playlist"}
    for r in get_resources("Python"):
        assert r["resource_type"] in valid
        assert r["url"].startswith("http")


def test_search_resources():
    results = search_resources("power bi")
    assert any("Power BI" in r["skill"] for r in results)


def test_all_curated_resources_valid():
    from src.resource_recommender import _load_resources

    for r in _load_resources():
        assert r["url"].startswith("http")
        assert r["title"]
        assert r["provider"]