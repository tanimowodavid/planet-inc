from django.test import TestCase

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch
from .models import Product, ProductVariant

class ProductSearchIntegrationTests(APITestCase):

    def setUp(self):
        # Create a baseline product and variant for testing
        self.product = Product.objects.create(
            name="Premium Running Shoes",
            description="High-performance lightweight footwear designed for marathon runners.",
            embedding=[0.1] * 1536  # Mocked baseline vector matching the field dimensions
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="Red / Size 10",
            price=120.00,
            stock_quantity=15,
            is_active=True
        )
        self.list_url = reverse("product-list")

    def test_homepage_lists_active_variants_with_pagination(self):
        """Verify the homepage endpoint returns paginated active variants without a search query."""
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify the structure matches our DRF PageNumberPagination format
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["sku"], self.variant.sku)

    @patch("product.views.generate_product_embedding")  # Adjust import string to match your project path
    def test_semantic_search_returns_relevant_results(self, mock_embedding):
        """Verify that passing a ?search parameter executes the pgvector logic successfully."""
        # Mock the embedding generator to return a matching 1536-dimension vector array
        mock_embedding.return_value = [0.1] * 1536
        
        response = self.client.get(self.list_url, {"search": "marathon sneakers"})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_embedding.assert_called_once_with("marathon sneakers")
        self.assertEqual(len(response.data["results"]), 1)

    @patch("product.views.generate_product_embedding")
    def test_semantic_search_graceful_fallback_on_api_failure(self, mock_embedding):
        """Verify that if the external embedding API fails, the view falls back to a basic text query."""
        # Force the embedding utility to raise an exception (e.g., timeout or rate limit)
        mock_embedding.side_effect = Exception("OpenAI API Down")
        
        # We search using a partial string that matches the product name for the fallback __icontains filter
        response = self.client.get(self.list_url, {"search": "Running"})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["sku"], self.variant.sku)
