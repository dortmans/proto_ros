#!/usr/bin/env python

"""This script translates Protobuf (proto) files into ROS Message (msg) files.

It uses Protobuf Compiler (protoc) with protoc_gen_msg plugin.

    Usage: proto2msg <proto_dir> <msg_dir> (--recursive)

For each proto file in proto_dir equivalent msg files are created in msg_dir.
"""

__author__ = 'eric.dortmans@gmail.com (Eric Dortmans)'


import argparse
from pathlib import Path
import subprocess
import logging
import sys

# Create logger
log = logging.getLogger('')
log.setLevel(logging.DEBUG)
sh = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(levelname)s %(message)s')
sh.setFormatter(formatter)
log.addHandler(sh)

# # Alternative for running protoc
# try:
#     import grpc_tools.protoc
# except ImportError:
#     print("Installation of grpcio-tools is required: 'pip install grpcio-tools'")
# import pkg_resources
# well_known_protos_include = pkg_resources.resource_filename(
#     "grpc_tools", "_proto"
# )


def main():

    log.info(f"Running this script: {Path(__file__)}")

    argparser = argparse.ArgumentParser(
        "Convert proto messages to ROS messages")
    argparser.add_argument("proto_dir", type=str, help="proto file directory")
    argparser.add_argument("msg_dir", type=str, help="msg file directory")
    argparser.add_argument("-r", "--recursive", action="store_true",
                           help="recurse proto file directory")
    args = argparser.parse_args()

    proto_dir = Path(args.proto_dir)
    msg_dir = Path(args.msg_dir)

    if not proto_dir.exists():
        log.error(f"Proto directory does not exist: {proto_dir}")
        raise SystemExit(1)
    if not msg_dir.exists():
        log.info(f"Creating msg directory: {msg_dir}")
        msg_dir.mkdir(parents=False, exist_ok=False)

    if args.recursive:
        proto_files = proto_dir.rglob('*.proto')
    else:
        proto_files = proto_dir.glob('*.proto')

    for proto_file in proto_files:
        log.info(f"Converting: {proto_file}")
        args = [
            'protoc',
            # f'--proto_path={well_known_protos_include}',
            f'--proto_path={proto_dir}',
            f'--msg_out={msg_dir}',
            str(proto_file)
        ]
        # grpc_tools.protoc.main(args)
        subprocess.run(args)


if __name__ == "__main__":
    main()
