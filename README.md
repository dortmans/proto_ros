# proto_ros

This project provides utilities for the translation between [Protocol Buffers](https://protobuf.dev/) message definitions (proto files) and [ROS message](https://docs.ros.org/en/rolling/Concepts/Basic/About-Interfaces.html#messages) definitions (msg files).

## proto2msg

The `proto2msg` script translates Protobuf (proto) files into equivalent ROS Message (msg) files.

Usage:
```
proto2msg <proto_dir> <msg_dir> (--recursive)
```

For each proto file in proto_dir equivalent msg files are created in msg_dir.

To translate a single protofile use the following command:
```
Usage: protoc --proto_path=<proto_dir> --msg_out=<msg_dir> <file.proto>
```

Limitations
- proto3 syntax
- enums are translated to constants
- No support for 'oneof' and 'any' types
- No support for extensions
- No support for options
- No support for service

The Protobuf Compiler (`protoc`) parses the proto file and provides it packed in a CodeGeneratorRequest to the `protoc_gen_msg` plugin (via stdin). This plugin generates a set of ROS message definition (msg) files from the parsed proto file. It returns the generated msg files packed in a CodeGeneratorResponse (via stdout) to the compiler.

## msg2proto

The `msg2proto` script translates ROS message (msg) files into Protobuf (proto) files.

Usage:
```
msg2proto <msg_dir> <proto_dir> (--package <packagename>)
```

For each msg file in msg_dir an equivalent proto file is created in proto_dir.

Limitations:
- proto3 syntax
- no support for default values (defaults are skipped)
- constants are translated to comments
- no support for string and array bounds (both treated as unbounded)

We defined a [Parsing Expression Grammar]((https://en.wikipedia.org/wiki/Parsing_expression_grammar)) for ROS messages and use [Parsimonious](https://github.com/erikrose/parsimonious) for the actual parsing.

## Installation

Install `protoc`, the Protobuf compiler:
```
sudo apt install protobuf-compiler
```

Install our `proto_ros` package from PyPi:
```
pip install proto_ros
```

Or install it from GitHub:
```
pip install "git+https://github.com/dortmans/proto_ros.git"
```



