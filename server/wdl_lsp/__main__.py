############################################################################
# Copyright(c) Open Law Library. All rights reserved.                      #
# See ThirdPartyNotices.txt in the project root for additional notices.    #
#                                                                          #
# Licensed under the Apache License, Version 2.0 (the "License")           #
# you may not use this file except in compliance with the License.         #
# You may obtain a copy of the License at                                  #
#                                                                          #
#     http: // www.apache.org/licenses/LICENSE-2.0                         #
#                                                                          #
# Unless required by applicable law or agreed to in writing, software      #
# distributed under the License is distributed on an "AS IS" BASIS,        #
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. #
# See the License for the specific language governing permissions and      #
# limitations under the License.                                           #
############################################################################
import argparse
import logging
from sys import stderr

from .server import server

def add_arguments(parser):
    parser.description = "WDL Language Server"

    parser.add_argument(
        "-t", "--tcp", action="store_true",
        help="Use TCP server instead of stdio"
    )
    parser.add_argument(
        "-a", "--address", default="127.0.0.1",
        help="Bind to this address"
    )
    parser.add_argument(
        "-p", "--port", type=int, default=2087,
        help="Bind to this port"
    )
    parser.add_argument(
        "-l", "--log", default="WARNING",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Minimum level for logging"
    )

def main():
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args()

    logging.basicConfig(
        stream = stderr,
        level = getattr(logging, args.log),
    )

    if args.tcp:
        server.start_tcp(args.address, args.port)
    else:
        server.start_io()

if __name__ == '__main__':
    main()
