import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from schools.models import GradeLevel, School


@pytest.fixture
def two_schools(db):
    a = School.objects.create(name="Alpha", code="ALPHA")
    b = School.objects.create(name="Beta", code="BETA")
    return a, b


from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient


@pytest.mark.django_db
def test_school_admin_cannot_see_other_school(api_client, two_schools):
    from django.contrib.auth import get_user_model

    a, b = two_schools
    User = get_user_model()
    GradeLevel.objects.create(school=a, name="G1", code="A1", level_order=1)
    GradeLevel.objects.create(school=b, name="G1", code="B1", level_order=1)
    admin = User.objects.create_user(
        username="a1", password="x", user_type="SCHOOL_ADMIN", school=a
    )
    client = api_client()
    client.force_authenticate(admin)
    response = client.get("/api/grade-levels/")
    assert response.status_code == 200
    results = response.json().get("results", response.json())
    assert len(results) == 1
    assert results[0]["code"] == "A1"
