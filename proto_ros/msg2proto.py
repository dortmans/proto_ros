#!/usr/bin/env python.

"""This script translates ROS message (msg) files into Protobuf (proto) files.

    Usage: msg2proto <msg_dir> <proto_dir> (--package <packagename>)

For each msg file in msg_dir an equivalent proto file is created in proto_dir.
"""

__author__ = 'eric.dortmans@gmail.com (Eric Dortmans)'

import os
import sys
import logging
import re
import argparse
from pathlib import Path
import numpy as np
from parsimonious.grammar import Grammar
from parsimonious.nodes import NodeVisitor
from parsimonious.exceptions import ParseError

DEBUG = False

# Create logger
log = logging.getLogger('')
sh = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(levelname)s %(message)s')
sh.setFormatter(formatter)
log.addHandler(sh)
if DEBUG:
    log.setLevel(logging.DEBUG)
else:
    log.setLevel(logging.INFO)

# ROS 2 MSG grammar (permissive, for data extraction only, not for validation)
# Ref: https://design.ros2.org/articles/legacy_interface_definition.html
# Ref: https://docs.ros.org/en/rolling/Concepts/Basic/About-Interfaces.html
grammar = Grammar(
    r"""
    msg             = (emptyline / line)*
    emptyline       = SP EOL
    line            = SP (comment / definition)? SP EOL
    definition      = constant / field
    field           = type SP fieldname SP !"=" value? SP comment?
    constant        = type SP constname SP "=" SP value SP comment?
    comment         = "#"+ SP text
    type            = basetype arrayspec?
    arrayspec       = "[" arraybound? "]"
    basetype        = complextype / stringtype / primitivetype 
    complextype     = (packagename "/")? msgname
    stringtype      = "string" stringbound?
    primitivetype   = ~r"[a-z0-9]+"
    arraybound      = ~r"(<=)?\d+"
    stringbound     = ~r"<=\d+"
    msgname         = ~r"[A-Z]\w*"
    packagename     = ~r"[a-z][a-z_]*"
    fieldname       = ~r"[a-z][a-z\d_]*"
    constname       = ~r"[A-Z][A-Z\d_]*"
    value           = numericval / boolval / stringval / arrayval 
    numericval      = ~r"[-+\.bBoOxX\d]+"
    boolval         = ~r"[Tt]rue" / ~r"[Ff]alse"
    stringval       = ~r"[a-z]?\"[^\"]*\"" / ~r"[a-z]?\'[^\']*\'"
    arrayval        = ~r"\[[^\]]*\]"
    text            = ~r".*"  
    SP              = ~r"[ \t]*"
    EOL             = ~r"[\n\r]"
    """
)


def to_snake_case(name):
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    name = re.sub('__([A-Z])', r'_\1', name)
    name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
    return name.lower()


def asscalar(array):
    return np.array(array).item()


class MsgVisitor(NodeVisitor):
    def visit_msg(self, node, visited_children):
        """ Returns the overall output. """
        output = list()
        for child in visited_children:
            output.append(asscalar(child))
        return output

    def visit_emptyline(self, node, visited_children):
        return {"emptyline": ""}

    def visit_line(self, node, visited_children):
        return visited_children[1]

    def visit_comment(self, node, visited_children):
        comment = asscalar(visited_children[2])
        return {"comment": comment}

    def visit_definition(self, node, visited_children):
        return visited_children[0]

    def visit_field(self, node, visited_children):
        type = asscalar(visited_children[0])
        name = asscalar(visited_children[2])
        value = asscalar(visited_children[5]) or {"value": ""}
        comment = asscalar(visited_children[7]) or {"comment": ""}
        params = {}
        params.update(type)
        params.update(name)
        params.update(value)
        params.update(comment)
        return {"field": params}

    def visit_constant(self, node, visited_children):
        type = asscalar(visited_children[0])
        name = asscalar(visited_children[2])
        value = asscalar(visited_children[6]) or {"value": ""}
        comment = asscalar(visited_children[8]) or {"comment": ""}
        params = {}
        params.update(type)
        params.update(name)
        params.update(value)
        params.update(comment)
        return {"constant": params}

    def visit_type(self, node, visited_children):
        basetype = asscalar(visited_children[0])
        arrayspec = asscalar(visited_children[1]) or {"is_array": False}
        log.debug(f"visit_type basetype: {basetype}, arrayspec: {arrayspec}")
        params = {}
        params.update(basetype)
        params.update(arrayspec)
        return {"type": params}

    def visit_arrayspec(self, node, visited_children):
        arraybound = asscalar(visited_children[1])
        return {"is_array": True, "arraybound": arraybound}

    def visit_basetype(self, node, visited_children):
        return visited_children[0]

    def visit_complextype(self, node, visited_children):
        if visited_children[0]:
            package = asscalar(visited_children[0][0][0]) or ''
        else:
            package = ''
        msgname = asscalar(visited_children[1])
        # log.debug(f"visit_complextype package: {package}, typename: {msgname}")
        return {"package": package, "typename": msgname, "is_complextype": True}

    def visit_stringtype(self, node, visited_children):
        # log.debug(f"visit_stringtype")
        return {"package": "", "typename": "string"}

    def visit_primitivetype(self, node, visited_children):
        # log.debug(f"visit_primitivetype typename: {node.text}")
        return {"package": "", "typename": node.text}

    def visit_packagename(self, node, visited_children):
        # log.debug(f"visit_packagename packagename: {node.text}")
        return node.text

    def visit_msgname(self, node, visited_children):
        # log.debug(f"visit_msgname msgname: {node.text}")
        return node.text

    def visit_fieldname(self, node, visited_children):
        return {"name": node.text}

    def visit_constname(self, node, visited_children):
        return {"name": node.text}

    def visit_value(self, node, visited_children):
        value = asscalar(visited_children[0])
        return {"value": value}

    def generic_visit(self, node, visited_children):
        """ The generic visit method. """
        return visited_children or node.text


def parse_msg(msg):
    tree = None
    parsed_msg = None
    # Use the grammar to parse the msg file into an abstract syntax tree
    try:
        tree = grammar.parse(msg)
    except ParseError as e:
        log.debug(e)
    # Visit the tree to transform it into semantical concepts
    if tree is not None:
        msg_visitor = MsgVisitor()
        parsed_msg = msg_visitor.visit(tree)
        return parsed_msg


def generate_proto(parsed_msg, msg_name, package):
    """ Generate a protobuf file from the parsed msg file """

    INDENT = "  "

    proto = f'// This file was generated. DO NOT EDIT!\n'
    proto += '\n'
    proto += f'syntax = "proto3";\n'

    if package != "":
        proto += '\n'
        proto += f'package {package};\n'

    message = f"message {msg_name} {{\n"
    fieldnumber = 1
    imports = set()
    for line in parsed_msg:
        line_type = list(line.keys())[0]
        if line_type == "emptyline":
            message += f"\n"
        if line_type == "comment":
            comment = line[line_type]
            comment = f"// {comment}"
            message += f"{INDENT}{comment}\n"
        if line_type == "field":
            field = f"{INDENT}"
            type = line[line_type]["type"]

            label = "repeated" if type.get("is_array") else ""
            if label:
                field += f"{label} "
            typename = type["typename"]

            namespace = type["package"]
            if namespace:
                typename = f"{namespace}/{typename}"

            typename = map_type(typename)

            if type.get("is_complextype"):
                # import required
                typename_parts = typename.split('.')
                if len(typename_parts) == 1:  # does not have namespace?
                    # add current packagename as namespace
                    typename_parts.insert(0, package)
                if typename_parts[-1] != msg_name:  # no recursion ?
                    # add to imports
                    typename_parts[-1] = to_snake_case(typename_parts[-1])
                    imports.add('/'.join(typename_parts))

            field += f"{typename} "
            name = line[line_type]["name"]
            field += f"{name} = {fieldnumber};"
            fieldnumber += 1
            comment = line[line_type]["comment"]
            bound = type.get("arraybound")
            if bound:
                comment = f"[{bound}] {comment}"
            if comment:
                field += f" // {comment}"
            message += f"{field}\n"
        if line_type == "constant":
            constant = f"{INDENT}// "
            constant += f"{INDENT}"
            name = line[line_type]["name"]
            value = line[line_type]["value"]
            constant += f"{name} = {value};"
            comment = line[line_type]["comment"]
            if comment:
                constant += f" // {comment}"
            message += f"{constant}\n"
    message += f"}}"

    if imports:
        proto += '\n'
        for i in imports:
            proto += f'import "{i}.proto";\n'

    proto += '\n'
    proto += message

    log.debug(proto)
    return proto


def convert_msg_file(msg_file, package, proto_dir):
    msg_name = msg_file.stem
    msg = msg_file.read_text(encoding="utf-8")
    parsed_msg = parse_msg(msg)
    if parsed_msg:
        proto = generate_proto(parsed_msg, msg_name, package)
        # proto_file = Path(proto_dir / package / msg_file.with_suffix(".proto").name)
        proto_file = Path(proto_dir / package /
                          f"{to_snake_case(msg_name)}.proto")
        log.info(f"Generating: {proto_file}")
        proto_file.parent.mkdir(parents=True, exist_ok=True)
        proto_file.write_text(proto, encoding="utf-8")


def map_type(field_type):
    map = {
        "float64": "double",
        "float32": "float",
        "int64": "int64",
        "uint64": "uint64",
        "int32": "int32",
        "uint32": "uint32",
        "int16": "int32",
        "uint16": "uint32",
        "int8": "int32",
        "uint8": "uint32",
        "byte": "uint32",
        "bool": "bool",
        "char": "string",
        "string": "string",
        "wstring": "string",
        "Header": "std_msgs.Header",
        "builtin_interfaces/Time": "google.protobuf.Timestamp",
        "builtin_interfaces/Duration": "google.protobuf.Duration",
        "std_msgs/Float64": "google.protobuf.DoubleValue",
        "std_msgs/Float32": "google.protobuf.FloatValue",
        "std_msgs/Int64": "google.protobuf.Int64Value",
        "std_msgs/UInt64": "google.protobuf.UInt64Value",
        "std_msgs/Int32": "google.protobuf.Int32Value",
        "std_msgs/UInt32": "google.protobuf.UInt32Value",
        "std_msgs/Bool": "google.protobuf.BoolValue",
        "std_msgs/String": "google.protobuf.StringValue",
        "std_msgs/String": "google.protobuf.BytesValue",

    }
    return map.get(field_type, field_type.replace('/', '.'))


def main():

    log.info(f"Running this script: {Path(__file__)}")

    argparser = argparse.ArgumentParser(
        "Convert ROS msg to protobuf proto")
    argparser.add_argument("msg_dir", type=str, help="msg file directory")
    argparser.add_argument("proto_dir", type=str, help="proto file directory")
    # argparser.add_argument("package", type=str,  help="package name")
    argparser.add_argument("--package", type=str,
                           default="", help="package name")
    args = argparser.parse_args()

    msg_dir = Path(args.msg_dir)
    proto_dir = Path(args.proto_dir)
    package = args.package

    if not msg_dir.exists():
        log.error(f"msg directory does not exist: {msg_dir}")
        raise SystemExit(1)
    if not proto_dir.exists():
        log.info(f"Creating proto directory: {proto_dir}")
        proto_dir.mkdir(parents=False, exist_ok=False)

    # Convert all msg files in the "msg_dir" folder
    msg_files = msg_dir.glob('*.msg')
    for msg_file in msg_files:
        log.info(f"Converting: {msg_file}")
        convert_msg_file(msg_file, package, proto_dir)


if __name__ == "__main__":
    main()
