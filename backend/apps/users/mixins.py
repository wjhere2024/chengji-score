class SchoolScopedQuerysetMixin:
    school_field = "class_obj__school"
    head_teacher_field = "class_obj__head_teacher"
    enable_role_filtering = False

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if getattr(user, "is_admin", False):
            if getattr(user, "school", None):
                return queryset.filter(**{self.school_field: user.school})
            return queryset

        if getattr(user, "school", None):
            queryset = queryset.filter(**{self.school_field: user.school})

        return queryset.filter(**{self.head_teacher_field: user})
