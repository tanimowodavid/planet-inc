from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.pagination import PageNumberPagination
from django.db import transaction
from django.shortcuts import get_object_or_404
from pgvector.django import CosineDistance

from .models import Product, ProductVariant
from .serializers import ProductSerializer, CategorySerializer, ProductVariantListSerializer, ProductVariantDetailSerializer
from .utils import generate_product_embedding


# Custom pagination manager for product listings
class ProductPagination(PageNumberPagination):
    page_size = 12  # Numbers of items per page on home page
    page_size_query_param = 'page_size'
    max_page_size = 100


class CategoryCreateView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = CategorySerializer(data=request.data)

        if serializer.is_valid():
            category = serializer.save()
            return Response(
                CategorySerializer(category).data,
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class ProductCreateView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                # Wrap in a transaction so if variant creation fails, 
                # the product isn't created either (Atomic)
                with transaction.atomic():
                    serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductUpdateView(APIView):
    permission_classes = [IsAdminUser]

    def put(self, request, slug):
        product = get_object_or_404(Product.all_objects, slug=slug)
        serializer = ProductSerializer(product, data=request.data, partial=True)

        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VariantListView(APIView):
    permission_classes = [AllowAny]
    pagination_class = ProductPagination

    def get(self, request):
        variants = ProductVariant.objects.filter(
            is_active=True,
            product__is_active=True
        ).select_related("product")

        # Check if this is a search request
        search_query = request.query_params.get('search', None)
        
        if search_query:
            try:
                # Convert the natural language search string into a 1536-dim vector
                query_vector = generate_product_embedding(search_query)
                
                # Annotate distance using pgvector on the related product embedding field
                variants = variants.annotate(
                    distance=CosineDistance('product__embedding', query_vector)
                ).order_by('distance')
                
            except Exception as e:
                # Fallback gracefully to basic text match if the embedding API down/fails
                print(f"Embedding error: {e}")
                variants = variants.filter(product__name__icontains=search_query).order_by('id')
        else:
            # If no search query, order by creation date (newest first)
            variants = variants.order_by('-product__created_at')

        # Apply standard DRF pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(variants, request, view=self)
        
        if page is not None:
            serializer = ProductVariantListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        # Fallback if pagination is turned off
        serializer = ProductVariantListSerializer(variants, many=True)
        return Response(serializer.data)


class VariantDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, sku):
        variant = get_object_or_404(
            ProductVariant.objects.select_related("product"),
            sku=sku,
            is_active=True,
            product__is_active=True
        )
        serializer = ProductVariantDetailSerializer(variant)
        return Response(serializer.data)

