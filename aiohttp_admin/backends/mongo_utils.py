import re
import trafaret as t
from trafaret.contrib.object_id import MongoId

from ..exceptions import JsonValidaitonError


__all__ = ['create_validator', 'create_filter']


def op(filter, field, operation, value):
    if operation == 'in':
        filter[field] = {'$in': value}
    elif operation == 'like':
        filter[field] = {'$regex': '^{}'.format(re.escape(value))}
    elif operation == 'eq':
        filter[field] = {'$eq': value}
    elif operation == 'ne':
        filter[field] = {'$ne': value}
    elif operation == 'le':
        filter[field] = {'$lte': value}
    elif operation == 'lt':
        filter[field] = {'$lt': value}
    elif operation == 'gt':
        filter[field] = {'$gt': value}
    elif operation == 'ge':
        filter[field] = {'$gte': value}
    else:
        raise ValueError('Operation not supported {}'.format(operation))
    return filter


# TODO: fix comparators, keys should be something better
comparator_map = {
    t.String: ['eq', 'ne', 'like'],
    t.Int: ['eq', 'ne', 'lt', 'le', 'gt', 'ge', 'in'],
    t.Float: ['eq', 'ne', 'lt', 'le', 'gt', 'ge'],
    # t.Date: ['eq', 'ne', 'lt', 'le', 'gt', 'ge'],
}


def check_comparator(column, comparator):
    # TODO: fix error messages and types
    if type(column.type) not in comparator_map:
        msg = 'Filtering for column type {} not supported'.format(column.type)
        raise Exception(msg)

    if comparator not in comparator_map[type(column.type)]:
        msg = 'Filtering for column type {} not supported'.format(column.type)
        raise Exception(msg)


def apply_trafaret(trafaret, value):
    validate = trafaret.check_and_return
    if isinstance(trafaret, MongoId):
        validate = trafaret.converter
    if isinstance(value, list):
        value = [validate(v) for v in value]
    else:
        value = validate(value)
    return value


def check_value(schema, field_name, value):
    try:
        keys = {s.name: s.trafaret for s in schema.keys}
        trafaret = keys.get(field_name)
        value = apply_trafaret(trafaret, value)

    except t.DataError as exc:
        raise JsonValidaitonError(**exc.as_dict())
    return value


def create_filter(filter, schema):
    query = {}
    for field_name, operation in filter.items():
        if isinstance(operation, dict):
            for op_name, value in operation.items():
                value = check_value(schema, field_name, value)
                query = op(query, field_name, op_name, value)
        else:
            value = operation
            value = check_value(schema, field_name, value)
            query[field_name] = value
    return query


def create_validator(schema, primary_key):
    keys = [s for s in schema.keys if s.get_name() != primary_key]
    new_schema = t.Dict({})
    new_schema.keys = keys
    return new_schema