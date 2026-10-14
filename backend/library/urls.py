from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BookCategoryViewSet, BookCopyViewSet, BookViewSet, BorrowingViewSet

router = DefaultRouter()
router.register("book-categories", BookCategoryViewSet, basename="book-category")
router.register("books", BookViewSet, basename="book")
router.register("book-copies", BookCopyViewSet, basename="book-copy")
router.register("borrowings", BorrowingViewSet, basename="borrowing")

urlpatterns = [path("", include(router.urls))]
