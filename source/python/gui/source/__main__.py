################################################################################
# Copyright (c) 2021 - 2022 Advanced Micro Devices, Inc. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
################################################################################

from __future__ import absolute_import

import sys
import argparse
import os.path
import dash
import dash_bootstrap_components as dbc
import copy
import json
import glob
import pandas as pd

from pathlib import Path
from yaml import parse
from collections import OrderedDict

from . import gui
from .parser import parseFiles
from .parser import getSpeedupData, compute_speedups, get_validations, process_data, compute_sorts


def causal(args):
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])

    # TODO This will become a glob to look for subfolders with coz files
    #workload_path = glob.glob(os.path.join(args.path, "*"), recursive=True)
    workload_path = [args.path]


    #speedup_df = parseFiles(workload_path, args, CLI)
    workload_path = workload_path[0]
    num_stddev = args.stddev
    num_speedups = len(args.speedups)

    if num_speedups > 0 and args.num_points > num_speedups:
        args.num_points = num_speedups

    data = {}
    inp = args.path
    with open(inp, "r") as f:
        inp_data = json.load(f)
        data = process_data(data, inp_data, args.experiments, args.progress_points)

    results_df = compute_sorts(compute_speedups(data, args.speedups, args.num_points, args.validate, args.cli))

    if not args.cli:
        runs = OrderedDict({workload_path: results_df})
        kernel_names = ["program1", "program2"]
        max_points = 9
        sortOptions = ["Alphabetical", "Max Speedup", "Min Speedup", "Impact"]
        input_filters = [
            {
                "Name": "Sort by",
                "filter": [],
                "values": list(
                    map(
                        str,
                        sortOptions,
                    )
                ),
                "type": "Name",
            },
            {
                "Name": "points",
                "filter": [],
                "values": max_points,
                "type": "int",
            },
        ]

        gui.build_causal_layout(
            app,
            runs,
            input_filters,
            workload_path,
            results_df,
            args.verbose,
        )
        app.run_server(
            debug=True if args.verbose >= 3 else False,
            host=args.ip_address,
            port=args.ip_port,
        )


def main():
    # omnitrace version
    this_dir = Path(__file__).resolve().parent
    if os.path.basename(this_dir) == "source":
        ver_path = os.path.join(f"{this_dir.parent}", "VERSION")
    else:
        ver_path = os.path.join(f"{this_dir}", "VERSION")
    f = open(ver_path, "r")
    VER = f.read()

    settings = {}
    if os.path.basename(this_dir) == "source":
        settings_path = os.path.join(f"{this_dir.parent}", "settings.json")
    else:
        settings_path = os.path.join(f"{this_dir}", "settings.json")
    
    if os.path.exists(settings_path):
        with open(settings_path,"r") as f:
            settings = json.load(f)
    else :
        f = open(settings_path,"w")

    my_parser = argparse.ArgumentParser(
        description="AMD's OmniTrace GUI",
        prog="tool",
        allow_abbrev=False,
        formatter_class=lambda prog: argparse.RawTextHelpFormatter(
            prog, max_help_position=40
        ),
        usage="""
                                        \nomnitrace-causal-plot --path <path>

                                        \n\n-------------------------------------------------------------------------------
                                        \nExamples:
                                        \n\tomnitrace-causal-plot --path workloads/toy
                                        \n-------------------------------------------------------------------------------\n
                                        """,
    )
    #my_parser.add_argument(
    #    "-V",
    #    "--version",
    #    action="version",
    #    version="Causal Visualizer (" + VER + ")",
    #)

    my_parser.add_argument(
        "-w",
        "--workload",
        metavar="FOLDER",
        type=str,
        dest="path",
        default=settings["path"]
        if "path" in settings
        else os.path.join(os.path.dirname(__file__), "workloads", "toy"),
        required=False,
        help="Specify path to causal profiles.\n(DEFAULT: {}/workloads/<name>)".format(
            os.getcwd()
        ),
    )

    my_parser.add_argument(
        "-V",
        "--verbose",
        help="Increase output verbosity",
        default=0,
        type=int,
    )

    my_parser.add_argument(
        "--ip",
        "--ip-addr",
        metavar="IP_ADDR",
        type=str,
        dest="ip_address",
        default="0.0.0.0",
        help="Specify the IP address for the web app.\n(DEFAULT: 0.0.0.0)",
    )

    my_parser.add_argument(
        "--port",
        "--ip-port",
        metavar="PORT",
        type=int,
        dest="ip_port",
        default=8051,
        help="Specify the port number for the IP address for the web app.\n(DEFAULT: 8051)",
    )

    # only CLI
    my_parser.add_argument(
        "-c",
        "--cli",
        action="store_true",
        default=settings["cli"]
        if "cli" in settings 
        else False,
        required=False,
    )
    my_parser.add_argument(
        "-e", "--experiments", type=str, help="Regex for experiments", default=".*"
    )
    my_parser.add_argument(
        "-p",
        "--progress-points",
        type=str,
        help="Regex for progress points",
        default=".*",
    )
    my_parser.add_argument(
        "-n", "--num-points", type=int, help="Minimum number of data points", default=5
    )
    my_parser.add_argument(
        "-s",
        "--speedups",
        type=int,
        help="List of speedup values to report",
        nargs="*",
        default=[],
    )
    my_parser.add_argument(
        "-d",
        "--stddev",
        type=int,
        help="Number of standard deviations to report",
        default=1,
    )
    my_parser.add_argument(
        "-v",
        "--validate",
        type=str,
        nargs="*",
        help="Validate speedup: {experiment regex} {progress-point regex} {virtual-speedup} {expected-speedup} {tolerance}",
        default=[],
    )

    args = my_parser.parse_args()

    settings["cli"] = args.cli
    settings["path"] = args.path
    with open(settings_path, "w") as f:
        f.write(json.dumps(settings, indent=4))
        
    causal(args)

    
    


if __name__ == "__main__":
    main()
