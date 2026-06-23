"""Unit tests for extraction strategies."""

from __future__ import annotations

import pytest

from webgateway.post_processing.strategies.json_ld import JsonLdStrategy
from webgateway.post_processing.strategies.meta_extract import MetaExtractStrategy


@pytest.fixture
def strategy() -> JsonLdStrategy:
    return JsonLdStrategy()


class TestJsonLdStrategy:
    async def test_extract_product_json_ld(self, strategy: JsonLdStrategy):
        html = """
        <html><head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Test Product",
            "description": "A test product",
            "offers": {
                "@type": "Offer",
                "price": "29.99",
                "priceCurrency": "USD",
                "availability": "https://schema.org/InStock"
            },
            "aggregateRating": {
                "@type": "AggregateRating",
                "ratingValue": "4.5",
                "reviewCount": "123"
            },
            "brand": {"@type": "Brand", "name": "TestBrand"},
            "sku": "TST-001"
        }
        </script>
        </head><body><p>Some content</p></body></html>
        """
        result = await strategy.extract(html, "https://example.com/product")
        assert result is not None
        assert "Test Product" in result.content
        assert "29.99" in result.content
        assert "4.5" in result.content
        assert "In Stock" in result.content
        assert result.structured_data is not None
        assert result.structured_data["@type"] == "Product"

    async def test_no_json_ld_returns_none(self, strategy: JsonLdStrategy):
        html = "<html><body><p>No structured data here</p></body></html>"
        result = await strategy.extract(html, "https://example.com")
        assert result is None

    async def test_empty_json_ld_returns_none(self, strategy: JsonLdStrategy):
        html = """
        <html><head>
        <script type="application/ld+json"></script>
        </head></html>
        """
        result = await strategy.extract(html, "https://example.com")
        assert result is None

    async def test_malformed_json_ld_ignored(self, strategy: JsonLdStrategy):
        html = """
        <html><head>
        <script type="application/ld+json">{invalid</script>
        <script type="application/ld+json">
        {"@type": "Product", "name": "Valid Product"}
        </script>
        </head></html>
        """
        result = await strategy.extract(html, "https://example.com")
        assert result is not None
        assert "Valid Product" in result.content

    async def test_higher_priority_type_wins(self, strategy: JsonLdStrategy):
        html = """
        <html><head>
        <script type="application/ld+json">
        {"@type": "WebPage", "name": "Generic Page"}
        </script>
        <script type="application/ld+json">
        {"@type": "Product", "name": "Real Product", "description": "desc"}
        </script>
        </head></html>
        """
        result = await strategy.extract(html, "https://example.com")
        assert result is not None
        assert "Real Product" in result.content
        assert "Generic Page" not in result.content

    async def test_article_flattens_to_readable_markdown(self, strategy: JsonLdStrategy):
        html = """
        <html><head>
        <script type="application/ld+json">
        {
            "@type": "Recipe",
            "name": "Test Recipe",
            "description": "A delicious recipe",
            "author": {"@type": "Person", "name": "Chef"},
            "datePublished": "2024-01-15"
        }
        </script>
        </head></html>
        """
        result = await strategy.extract(html, "https://example.com/recipe")
        assert result is not None
        assert "# Test Recipe" in result.content
        assert "Chef" in result.content
        assert "2024-01-15" in result.content

    async def test_strategy_result_has_structured_data(self, strategy: JsonLdStrategy):
        html = """
        <html><head>
        <script type="application/ld+json">
        {"@type": "Product", "name": "JSON Product", "price": "9.99"}
        </script>
        </head></html>
        """
        result = await strategy.extract(html, "https://example.com/p")
        assert result is not None
        assert result.structured_data is not None
        assert result.structured_data["name"] == "JSON Product"

    async def test_multiple_types_in_list(self, strategy: JsonLdStrategy):
        html = """
        <html><head>
        <script type="application/ld+json">
        {"@type": ["Product", "Book"], "name": "Multi-Type Item", "isbn": "123"}
        </script>
        </head></html>
        """
        result = await strategy.extract(html, "https://example.com/multi")
        assert result is not None
        assert "Multi-Type Item" in result.content

    async def test_handles_graph_array(self, strategy: JsonLdStrategy):
        html = """
        <html><head>
        <script type="application/ld+json">
        {"@graph": [
            {"@type": "WebPage", "name": "Page"},
            {"@type": "Product", "name": "Graph Product", "description": "from @graph"}
        ]}
        </script>
        </head></html>
        """
        result = await strategy.extract(html, "https://example.com/graph")
        assert result is not None
        assert "Graph Product" in result.content


@pytest.fixture
def meta_strategy() -> MetaExtractStrategy:
    return MetaExtractStrategy()


class TestMetaExtractStrategy:
    async def test_extract_og_tags(self, meta_strategy: MetaExtractStrategy):
        html = """
        <html><head>
        <title>Test Article</title>
        <meta property="og:title" content="OG Test Article">
        <meta property="og:description" content="An OG description">
        <meta property="og:image" content="https://example.com/image.jpg">
        <meta name="description" content="A meta description">
        <meta name="keywords" content="test, article">
        </head><body><p>Body content</p></body></html>
        """
        result = await meta_strategy.extract(html, "https://example.com")
        assert result is not None
        assert "OG Test Article" in result.content
        assert "An OG description" in result.content
        assert result.structured_data is not None
        assert result.structured_data["og:title"] == "OG Test Article"

    async def test_twitter_cards(self, meta_strategy: MetaExtractStrategy):
        html = """
        <html><head>
        <meta name="twitter:card" content="summary_large_image">
        <meta name="twitter:site" content="@test">
        <meta name="twitter:creator" content="@author">
        </head></html>
        """
        result = await meta_strategy.extract(html, "https://example.com")
        assert result is not None
        assert "summary_large_image" in result.content
        assert "@test" in result.content

    async def test_no_meta_returns_none(self, meta_strategy: MetaExtractStrategy):
        html = "<html><body><p>No meta here</p></body></html>"
        result = await meta_strategy.extract(html, "https://example.com")
        assert result is None

    async def test_title_only(self, meta_strategy: MetaExtractStrategy):
        html = "<html><head><title>Just a title</title></head><body></body></html>"
        result = await meta_strategy.extract(html, "https://example.com")
        assert result is not None
        assert "Just a title" in result.content
