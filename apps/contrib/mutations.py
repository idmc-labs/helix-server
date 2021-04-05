import graphene
from graphene_file_upload.scalars import Upload

from apps.contrib.schema import AttachmentType
from apps.contrib.serializers import AttachmentSerializer
from utils.error_types import CustomErrorType, mutation_is_not_valid
from utils.permissions import is_authenticated


class AttachmentCreateInputType(graphene.InputObjectType):
    attachment = Upload(required=True)
    attachment_for = graphene.String(required=True)


class CreateAttachment(graphene.Mutation):
    class Arguments:
        data = AttachmentCreateInputType(required=True)

    errors = graphene.List(CustomErrorType)
    ok = graphene.Boolean()
    result = graphene.Field(AttachmentType)

    @staticmethod
    @is_authenticated()
    def mutate(root, info, data):
        serializer = AttachmentSerializer(data=data,
                                          context={'request': info.context.request})
        if errors := mutation_is_not_valid(serializer):
            return CreateAttachment(errors=errors, ok=False)
        instance = serializer.save()
        return CreateAttachment(result=instance, errors=None, ok=True)


class Mutation:
    create_attachment = CreateAttachment.Field()
