import graphene

import apps.users.schema


class Query(graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query)
