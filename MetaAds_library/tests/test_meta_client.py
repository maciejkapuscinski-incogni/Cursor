from meta_ads.meta_client import MetaAdsClient


def test_build_params_omits_search_type_without_query() -> None:
    client = MetaAdsClient(access_token="test-token")

    params = client._build_params(
        query=None,
        countries=["US"],
        page_ids=["123456"],
        media_type=None,
        active_status="ALL",
        search_type="KEYWORD_UNORDERED",
    )

    assert params["search_page_ids"] == '["123456"]'
    assert "search_terms" not in params
    assert "search_type" not in params


def test_build_params_includes_search_type_with_query() -> None:
    client = MetaAdsClient(access_token="test-token")

    params = client._build_params(
        query="incogni",
        countries=["US"],
        page_ids=None,
        media_type="VIDEO",
        active_status="ALL",
        search_type="KEYWORD_UNORDERED",
    )

    assert params["search_terms"] == "incogni"
    assert params["search_type"] == "KEYWORD_UNORDERED"
