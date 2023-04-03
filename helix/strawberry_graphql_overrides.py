# NOTE: Quick dirty fix.
from typing import Any

from graphql.execution.execute import ExecutionContext, get_field_def
from graphql.type import GraphQLObjectType
from graphql.language import FieldNode
from graphql.pyutils import AwaitableOrValue, Path, Undefined
from graphql.execution.values import get_argument_values
from graphql.error import located_error

import strawberry
from strawberry_django_plus.mutations.fields import DjangoMutationField
from strawberry_django_plus.utils.inspect import get_possible_types
from strawberry.annotation import StrawberryAnnotation
from strawberry_django_plus.types import OperationInfo
from strawberry.utils.str_converters import to_camel_case

from django.utils import translation


# Mutation fix [Start]
# https://github.com/blb-ventures/strawberry-django-plus/blob/v1.28.6/strawberry_django_plus/mutations/fields.py#L136-L148
@DjangoMutationField.type.setter
def django_mutation_field_type_setter(self, type_: Any) -> None:  # noqa:A003
    if type_ is not None and self._handle_errors:
        name = to_camel_case(self.python_name)
        cap_name = name[0].upper() + name[1:]
        if isinstance(type_, StrawberryAnnotation):
            type_ = type_.annotation
        types_ = tuple(get_possible_types(type_))
        # XXX: CUSTOM CHANGE: Added this check to make sure OperationInfo is not duplicate
        if OperationInfo not in types_:
            types_ += (OperationInfo,)
        type_ = strawberry.union(f"{cap_name}Payload", types_)

    self.type_annotation = type_


DjangoMutationField.type = django_mutation_field_type_setter
# Mutation fix [Stop]


# Graphql async + django translation quick fix [Start]
# https://github.com/graphql-python/graphql-core/blob/v3.2.1/src/graphql/execution/execute.py#L485-L559
def custom_execute_field(
    self,
    parent_type: GraphQLObjectType,
    source: Any,
    field_nodes: list[FieldNode],
    path: Path,
) -> AwaitableOrValue[Any]:
    field_def = get_field_def(self.schema, parent_type, field_nodes[0])
    if not field_def:
        return Undefined
    return_type = field_def.type
    resolve_fn = field_def.resolve or self.field_resolver
    if self.middleware_manager:
        resolve_fn = self.middleware_manager.get_field_resolver(resolve_fn)
    info = self.build_resolve_info(field_def, field_nodes, parent_type, path)
    try:
        args = get_argument_values(field_def, field_nodes[0], self.variable_values)
        result = resolve_fn(source, info, **args)
        active_language = translation.get_language()
        if self.is_awaitable(result):
            # noinspection PyShadowingNames
            async def await_result() -> Any:
                # XXX: CUSTOM CHANGE: ADDED `with translation.override(active_language):`
                with translation.override(active_language):
                    try:
                        completed = self.complete_value(
                            return_type, field_nodes, info, path, await result
                        )
                        if self.is_awaitable(completed):
                            return await completed
                        return completed
                    except Exception as raw_error:
                        error = located_error(raw_error, field_nodes, path.as_list())
                        self.handle_field_error(error, return_type)
                        return None
            return await_result()
        completed = self.complete_value(
            return_type, field_nodes, info, path, result
        )
        if self.is_awaitable(completed):
            # noinspection PyShadowingNames
            async def await_completed() -> Any:
                try:
                    return await completed
                except Exception as raw_error:
                    error = located_error(raw_error, field_nodes, path.as_list())
                    self.handle_field_error(error, return_type)
                    return None
            return await_completed()
        return completed
    except Exception as raw_error:
        error = located_error(raw_error, field_nodes, path.as_list())
        self.handle_field_error(error, return_type)
        return None


ExecutionContext.execute_field = custom_execute_field
# Graphql async + django translation quick fix [Start]
