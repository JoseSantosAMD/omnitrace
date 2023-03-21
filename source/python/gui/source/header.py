#!/usr/bin/env python3
# MIT License
#
# Copyright (c) 2023 Advanced Micro Devices, Inc. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
import dash_daq as daq
import dash_bootstrap_components as dbc

from dash import html, dash_table, dcc
from matplotlib.style import available


def file_path():
    return html.Li(
        className="filter",
        children=[
            dcc.Input(
                id="file-path",
                placeholder="Insert Workload directory",
                type="text",
                debounce=True,
            )
        ],
    )


def function_filter(_id, _placeholder):
    return html.Li(
        className="filter",
        children=[
            dcc.Input(
                id=_id,
                placeholder=_placeholder,
                type="text",
                debounce=True,
            )
        ],
    )


def upload_file():
    return html.Li(
        className="filter",
        children=[
            # drag and drop
            dcc.Upload(
                id="upload-drag",
                children=[html.A("Drag and Drop or Select a File")],
            )
        ],
    )


def minPoints(name, values):
    return html.Li(
        className="filter",
        id="min-points",
        children=[
            html.Div(
                children=[
                    html.A(children=["Min Points:"]),
                    daq.Slider(
                        min=0,
                        max=values,
                        step=1,
                        value=1,
                        id="points-filt",
                        handleLabel={"showCurrentValue": True, "label": " "},
                        size=120,
                    ),
                ],
            ),
        ],
    )


def sortBy(name, values, default, multi_):
    return html.Li(
        className="filter",
        children=[
            html.Div(
                children=[
                    html.A(children=[name + ":"]),
                    dcc.Dropdown(
                        values,
                        id=name + "-filt",
                        multi=multi_,
                        value=default,
                        clearable=False,
                    ),
                ],
            )
        ],
    )


def refresh():
    return html.Li(
        className="filter",
        children=[
            html.Button(
                className="refresh",
                children=["Refresh Data"],
                id="refresh",
            )
        ],
    )


def get_header(dropDownMenuItems, input_filters):
    children_ = [
        html.Nav(
            id="nav-wrap",
            children=[
                html.Ul(
                    id="nav",
                    children=[
                        html.Div(
                            className="nav-left",
                            children=[
                                dbc.DropdownMenu(
                                    dropDownMenuItems, label="Menu", menu_variant="dark"
                                )
                            ],
                        )
                    ],
                )
            ],
        )
    ]

    for filter in input_filters:
        header_nav = children_[0].children[0].children
        if filter["type"] == "int":
            header_nav.append(minPoints(filter["Name"], filter["values"]))
        elif filter["type"] == "Name":
            header_nav.append(
                sortBy(
                    filter["Name"],
                    filter["values"],
                    filter["default"],
                    filter["multi"],
                    # {},
                )
            )
        else:
            print("type not supported")
            # sys.exit(1)
    header_nav = children_[0].children[0].children
    header_nav.append(function_filter("function_regex", "Funtion/line regex"))
    header_nav.append(function_filter("exp_regex", "Experiment regex"))

    # header_nav.append(minPoints())

    header_nav.append(file_path())
    header_nav.append(upload_file())
    header_nav.append(refresh())

    return html.Header(id="home", children=children_)
