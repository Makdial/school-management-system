from rest_framework import serializers

from .models import Book, BookCategory, BookCopy, Borrowing


class BookCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BookCategory
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school"]


class BookCopySerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)

    class Meta:
        model = BookCopy
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class BookSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    copies = BookCopySerializer(many=True, read_only=True)

    class Meta:
        model = Book
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "school", "available_copies"]


class BorrowingSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="copy.book.title", read_only=True)
    borrower_name = serializers.CharField(source="borrower.full_name", read_only=True)
    copy_code = serializers.CharField(source="copy.copy_code", read_only=True)

    class Meta:
        model = Borrowing
        fields = "__all__"
        read_only_fields = [
            "id", "created_at", "updated_at", "school", "returned_at",
            "status", "fine_amount", "issued_by",
        ]
