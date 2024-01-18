# !/usr/bin/env python

import sys
import itertools
import json

from google.protobuf.compiler import plugin_pb2 as plugin
from google.protobuf.descriptor_pb2 import DescriptorProto, EnumDescriptorProto, FieldDescriptorProto, OneofDescriptorProto


def traverse(proto_file):

    def _traverse(package, items):
        for item in items:  # toplevel items
            yield item, package

            if isinstance(item, DescriptorProto):  # item is message
                for enum in item.enum_type:  # nested enums
                    nested_package = package + '.' + item.name
                    yield enum, package

                for nested_item in item.nested_type:  # nested messages
                    nested_package = package + '.' + item.name
                    yield nested_item, nested_package

    return itertools.chain(
        _traverse(proto_file.package, proto_file.enum_type),
        _traverse(proto_file.package, proto_file.message_type),
    )


def generate_code(request, response):
    error = None

    for proto_file in request.proto_file:
        output = []

        # Parse request
        for item, package in traverse(proto_file):
            data = {
                'package': package or '&lt;root&gt;',
                # 'package': proto_file.package or '&lt;root&gt;',
                'filename': proto_file.name,
                'name': item.name,
            }

            if isinstance(item, DescriptorProto):
                data.update({
                    'type': 'Message',
                    'properties': [{'name': f.name,
                                    'number': f.number,
                                    'label': map_label(f.label),
                                    'type': map_type(f.type),
                                    'type_name': f.type_name[1:],
                                    }
                                   for f in item.field]
                })

            elif isinstance(item, EnumDescriptorProto):
                data.update({
                    'type': 'Enum',
                    'values': [{'name': v.name, 'value': v.number}
                               for v in item.value]
                })

            output.append(data)

        # Fill response
        f = response.file.add()
        f.name = proto_file.name + '.json'
        f.content = json.dumps(output, indent=2)

    if error:
        response.error = error


def map_type(field_type):
    type_map = {
        FieldDescriptorProto.TYPE_DOUBLE: "TYPE_DOUBLE",
        FieldDescriptorProto.TYPE_FLOAT: "TYPE_FLOAT",
        FieldDescriptorProto.TYPE_INT64: "TYPE_INT64",
        FieldDescriptorProto.TYPE_UINT64: "TYPE_UINT64",
        FieldDescriptorProto.TYPE_INT32: "TYPE_INT32",
        FieldDescriptorProto.TYPE_FIXED64: "TYPE_FIXED64",
        FieldDescriptorProto.TYPE_FIXED32: "TYPE_FIXED32",
        FieldDescriptorProto.TYPE_BOOL: "TYPE_BOOL",
        FieldDescriptorProto.TYPE_STRING: "TYPE_STRING",
        FieldDescriptorProto.TYPE_GROUP: "TYPE_GROUP",
        FieldDescriptorProto.TYPE_MESSAGE: "TYPE_MESSAGE",
        FieldDescriptorProto.TYPE_BYTES: "TYPE_BYTES",
        FieldDescriptorProto.TYPE_UINT32: "TYPE_UINT32",
        FieldDescriptorProto.TYPE_ENUM: "TYPE_ENUM",
        FieldDescriptorProto.TYPE_SFIXED32: "TYPE_SFIXED32",
        FieldDescriptorProto.TYPE_SFIXED64: "TYPE_SFIXED64",
        FieldDescriptorProto.TYPE_SINT32: "TYPE_SINT32",
        FieldDescriptorProto.TYPE_SINT64: "TYPE_SINT64",
    }
    return type_map.get(field_type, field_type)


def map_label(label_type):
    label_map = {
        FieldDescriptorProto.LABEL_OPTIONAL: "LABEL_OPTIONAL",
        FieldDescriptorProto.LABEL_REPEATED: "LABEL_REPEATED",
        FieldDescriptorProto.LABEL_REQUIRED: "LABEL_REQUIRED",
    }
    return label_map.get(label_type, label_type)


def main():
    # Read binary request message from stdin
    data = sys.stdin.buffer.read()

    # Parse request
    request = plugin.CodeGeneratorRequest()
    request.ParseFromString(data)

    # Create response
    response = plugin.CodeGeneratorResponse()

    # Generate code
    generate_code(request, response)

    # Serialise response message
    output = response.SerializeToString()

    # Write binary output to stdout
    sys.stdout.buffer.write(output)


if __name__ == "__main__":
    main()
