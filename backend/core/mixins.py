from collections import deque

from django.core.exceptions import FieldDoesNotExist
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from .pagination import StandardPagination
from .permissions import IsSchoolMember


# Cache of model -> path to its ``school`` relation (or None). Resolved once per
# process because the result only depends on the model class.
_SCHOOL_PATH_CACHE: dict[type, str | None] = {}


def model_has_field(model, field_name):
    try:
        model._meta.get_field(field_name)
        return True
    except FieldDoesNotExist:
        return False


def resolve_school_relation(model, max_depth=4):
    """Return the ORM path from ``model`` to a ``school`` foreign key.

    Directly school-scoped models yield ``"school"``; models that are scoped
    through a parent yield the full path, e.g. ``"section__school"`` or
    ``"exam_subject__school"``. Returns ``None`` when no path exists.
    """
    if model in _SCHOOL_PATH_CACHE:
        return _SCHOOL_PATH_CACHE[model]

    path = None
    if model_has_field(model, "school"):
        path = "school"
    else:
        visited = {model}
        queue = deque([(model, "")])
        while queue and path is None:
            current, prefix = queue.popleft()
            for field in current._meta.get_fields():
                if not field.is_relation or field.auto_created:
                    continue
                if not (field.many_to_one or field.one_to_one):
                    continue
                related = field.related_model
                if related is None or related in visited:
                    continue
                candidate = f"{prefix}{field.name}"
                if field.name == "school":
                    path = candidate
                    break
                visited.add(related)
                if prefix.count("__") < max_depth:
                    queue.append((related, f"{candidate}__"))

    _SCHOOL_PATH_CACHE[model] = path
    return path


class SchoolScopedQuerysetMixin:
    """Restrict a queryset to the caller's school.

    Super administrators may pass ``?school=<id>`` to inspect a single
    institution; otherwise they see every institution. Regular users are
    always hard scoped to their own school which prevents cross-tenant
    leakage through URL manipulation.

    Models scoped indirectly (e.g. ``Classroom`` via ``section.school``) are
    supported automatically: the path to the ``school`` foreign key is resolved
    from the model graph.
    """

    # Optional explicit path to the school relation (e.g. "section__school").
    # When left unset it is detected automatically from the model.
    school_lookup = None

    def get_school_id(self):
        user = getattr(self.request, "user", None)
        if not user or not user.is_authenticated:
            return None
        if user.is_superuser or user.user_type == "SUPERADMIN":
            return self.request.query_params.get("school")
        return user.school_id

    def get_school_lookup(self, model):
        return self.school_lookup or resolve_school_relation(model)

    def get_queryset(self):
        qs = super().get_queryset()
        school_id = self.get_school_id()
        user = self.request.user
        is_super = user.is_superuser or user.user_type == "SUPERADMIN"
        if school_id:
            path = self.get_school_lookup(qs.model)
            if path:
                qs = qs.filter(**{f"{path}_id": school_id})
        elif not is_super:
            return qs.none()
        return qs

    def perform_create(self, serializer):
        if "school" in serializer.validated_data:
            return super().perform_create(serializer)
        model = serializer.Meta.model
        if model_has_field(model, "school"):
            school_id = self.get_school_id()
            user = self.request.user
            if not school_id and not (
                user.is_superuser or user.user_type == "SUPERADMIN"
            ):
                school_id = user.school_id
            return super().perform_create(serializer.save(school_id=school_id))
        # School is implied by the parent relation the client supplied.
        return super().perform_create(serializer)


class SchoolScopedViewSetMixin(SchoolScopedQuerysetMixin):
    permission_classes = [IsSchoolMember]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
