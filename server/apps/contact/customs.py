from graphene_django.types import ErrorType
from graphene_django_extras import DjangoSerializerMutation


class CustomDjangoSerializerMutation(DjangoSerializerMutation):
    class Meta:
        abstract = True

    @classmethod
    def create(cls, root, info, **kwargs):
        data = kwargs.get(cls._meta.input_field_name)
        request_type = info.context.META.get("CONTENT_TYPE", "")
        if "multipart/form-data" in request_type:
            data.update({name: value for name, value in info.context.FILES.items()})

        serializer = cls._meta.serializer_class(
            data=data, **cls.get_serializer_kwargs(root, info, **kwargs)
        )

        ok, obj = cls.save(serializer, root, info)
        if not ok:
            # todo checkme with a nested object... maybe not
            return cls.get_errors(obj)
        return cls.perform_mutate(obj, info)
