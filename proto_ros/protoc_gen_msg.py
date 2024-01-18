# !/usr/bin/env python

"""A Protobuf Compiler (protoc) plugin that generates a set of 
ROS message definition (msg) files from a parsed Protobuf (proto) file.

It receives a CodeGeneratorRequest with a parsed proto file on stdin 
and writes a CodeGeneratorResponse with generated msg files to stdout

Usage: protoc --proto_path=<proto_dir> --msg_out=<msg_dir> <protofile.proto>
"""

__author__ = 'eric.dortmans@gmail.com (Eric Dortmans)'


import sys
import logging

from google.protobuf.compiler import plugin_pb2 as plugin
from google.protobuf.descriptor_pb2 import FieldDescriptorProto

DEBUG = False

# Create logger
log = logging.getLogger('')
sh = logging.StreamHandler(sys.stderr)
formatter = logging.Formatter('%(levelname)s %(message)s')
sh.setFormatter(formatter)
log.addHandler(sh)
if DEBUG:
    log.setLevel(logging.DEBUG)


CONSTANT_FIELD_TYPE = "uint8"


def generate_code(request, response):
    proto_file = request.proto_file[-1]  # parse selected proto file only
    generate_msg_files(proto_file, response)


def generate_msg_files(proto_file, response):
    enums = collect_enums(proto_file)
    for message in proto_file.message_type:  # messages
        log.debug(f"\n<<<message: {message.name}>>>")
        generate_msg_file(message, proto_file.package, enums, response)
        for nested_message in message.nested_type:  # nested messages
            log.debug(f"\n<<<nested message: {nested_message.name}>>>")
            generate_msg_file(
                nested_message, proto_file.package, enums, response)


def collect_enums(proto_file):
    enums = proto_file.enum_type  # global enums
    for message in proto_file.message_type:
        enums.extend(message.enum_type)  # nested enums
    return enums


def generate_msg_file(message, package, enums, response):

    # Output message
    errors = None
    output, referenced_enums, errors = generate_message(message, package)

    # Add referenced enums
    for enum in enums:
        if enum.name in referenced_enums:
            log.debug(f"[[[enum: {enum.name}]]]")
            output += generate_enum(enum)
            referenced_enums.remove(enum.name)

    # Add output to response
    if errors:
        response.error = errors
    else:
        file = f"{package}/{message.name}.msg"
        log.debug(f"Generating: {file}")
        f = response.file.add()
        f.name = file
        f.content = output


def generate_message(message, package):
    errors = None
    referenced_enums = set()
    output = f'# This file was generated. DO NOT EDIT!\n\n'
    output += f'# {message.name}\n'
    for field in message.field:  # fields
        fieldname = field.name
        mapped_field_type = map_type(field.type)
        if mapped_field_type == 'TYPE_MESSAGE':  # field refers to message type ?
            fieldtype = field.type_name
            # message type lives in same package ?
            if fieldtype.split('.')[1] == package:
                # keep only the message type name
                fieldtype = fieldtype.split('.')[-1]
            else:
                fieldtype = fieldtype[1:]  # just remove first period character
            if fieldtype.startswith("google.protobuf"):  # is welknown type ?
                fieldtype = map_type_name(fieldtype)
            fieldtype = fieldtype.replace('.', '/')
            fieldcomment = ''
        elif mapped_field_type == 'TYPE_ENUM':  # field refers to enum ?
            enum_name = field.type_name.split(
                '.')[-1]  # keep only the enum type name
            referenced_enums.add(enum_name)
            fieldtype = CONSTANT_FIELD_TYPE
            fieldcomment = f'# {enum_name}'
        else:  # field has primitive type
            fieldtype = mapped_field_type
            fieldcomment = ''
        if map_label(field.label) == 'LABEL_REPEATED':  # is array ?
            fieldtype += '[]'
        output += f"{fieldtype} {fieldname} {fieldcomment}\n"
        log.debug(f"{fieldtype} {fieldname} {fieldcomment}")
    return output, referenced_enums, errors


def generate_enum(enum):
    output = f'\n# {enum.name}\n'
    for value in enum.value:
        output += f'{CONSTANT_FIELD_TYPE} {value.name}={value.number}\n'
        log.debug(f'{CONSTANT_FIELD_TYPE} {value.name}={value.number}')
    return output


def map_type(field_type):
    map = {
        FieldDescriptorProto.TYPE_DOUBLE: "float64",
        FieldDescriptorProto.TYPE_FLOAT: "float32",
        FieldDescriptorProto.TYPE_INT64: "int64",
        FieldDescriptorProto.TYPE_UINT64: "uint64",
        FieldDescriptorProto.TYPE_INT32: "int32",
        FieldDescriptorProto.TYPE_FIXED64: "uint64",
        FieldDescriptorProto.TYPE_FIXED32: "uint32",
        FieldDescriptorProto.TYPE_BOOL: "bool",
        FieldDescriptorProto.TYPE_STRING: "string",
        FieldDescriptorProto.TYPE_GROUP: "TYPE_GROUP",
        FieldDescriptorProto.TYPE_MESSAGE: "TYPE_MESSAGE",
        FieldDescriptorProto.TYPE_BYTES: "string",
        FieldDescriptorProto.TYPE_UINT32: "uint32",
        FieldDescriptorProto.TYPE_ENUM: "TYPE_ENUM",
        FieldDescriptorProto.TYPE_SFIXED32: "int32",
        FieldDescriptorProto.TYPE_SFIXED64: "int64",
        FieldDescriptorProto.TYPE_SINT32: "int32",
        FieldDescriptorProto.TYPE_SINT64: "int64",
    }
    return map.get(field_type, "string")


def map_type_name(field_type_name):
    map = {  # Wellknown types
        "google.protobuf.Timestamp": "builtin_interfaces/Time",
        "google.protobuf.Duration": "builtin_interfaces/Duration",
        "google.protobuf.Empty": "std_msgs/Empty",
        "google.protobuf.DoubleValue": "std_msgs/Float64",
        "google.protobuf.FloatValue": "std_msgs/Float32",
        "google.protobuf.Int64Value": "std_msgs/Int64",
        "google.protobuf.UInt64Value": "std_msgs/UInt64",
        "google.protobuf.Int32Value": "std_msgs/Int32",
        "google.protobuf.UInt32Value": "std_msgs/UInt32",
        "google.protobuf.BoolValue": "std_msgs/Bool",
        "google.protobuf.StringValue": "std_msgs/String",
        "google.protobuf.BytesValue": "std_msgs/String",
    }
    return map.get(field_type_name, "std_msgs/String")


def map_label(label_type):
    map = {
        FieldDescriptorProto.LABEL_OPTIONAL: "LABEL_OPTIONAL",
        FieldDescriptorProto.LABEL_REPEATED: "LABEL_REPEATED",
        FieldDescriptorProto.LABEL_REQUIRED: "LABEL_REQUIRED",
    }
    return map.get(label_type, label_type)


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
