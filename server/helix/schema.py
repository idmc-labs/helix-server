import graphene

import apps.users.schema


class Query(apps.users.schema.Query, 
            graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query)
