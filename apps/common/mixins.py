from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class BaseViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Base ViewSet with common CRUD operations.
    Includes filtering, searching, and ordering by default.
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    # Override these in subclasses
    filterset_fields = []
    search_fields = []
    ordering_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]


class ReadOnlyViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """
    Base ViewSet for read-only operations.
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    # Override these in subclasses
    filterset_fields = []
    search_fields = []
    ordering_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]


class CreateUpdateViewSet(
    mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    """
    Base ViewSet for create and update operations only.
    """

    permission_classes = [IsAuthenticated]


class BaseModelViewSet(BaseViewSet):
    """
    Enhanced BaseViewSet with additional common actions.
    """

    @action(detail=False, methods=["get"])
    def count(self, request):
        """Get count of objects."""
        queryset = self.filter_queryset(self.get_queryset())
        count = queryset.count()
        return Response({"count": count})

    @action(detail=False, methods=["delete"])
    def bulk_delete(self, request):
        """Bulk delete objects."""
        ids = request.data.get("ids", [])
        if not ids:
            return Response({"error": "No IDs provided for bulk delete"}, status=400)

        queryset = self.get_queryset().filter(id__in=ids)
        deleted_count = queryset.delete()[0]

        return Response(
            {
                "message": f"Successfully deleted {deleted_count} objects",
                "deleted_count": deleted_count,
            }
        )
