# import unittest
from seleniumwire import webdriver
import page
from pyvirtualdisplay import Display

# from selenium.webdriver.firefox.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

# from selenium.webdriver.chrome.options import Options
import subprocess
import sys, os
import time
import multiprocessing
import pandas as pd
import numpy as np

que = os.path.realpath(os.path.dirname(__file__) + "/..")
sys.path.append(que)
import pytest
from source.gui import build_causal_layout
from source.__main__ import causal, create_parser, default_settings
from source.parser import (
    parse_files,
    find_causal_files,
    set_num_stddev,
    parse_uploaded_file,
    process_data,
    compute_speedups,
)

import json

from pathlib import Path

path = Path(__file__).parent.absolute()


workload_dir = os.path.realpath(
    os.path.join(
        path,
        *"../workloads/omnitrace-tests-output/causal-cpu-omni-fast-func-e2e/causal".split(
            "/"
        ),
    )
)

titles = [
    "Selected Causal Profiles",
    "/home/jose/omnitrace/examples/causal/causal.cpp:165",
    "cpu_fast_func(long, int)",
    "cpu_slow_func(long, int)",
]

samples_df_expected_locations = [
    "/home/jose/omnitrace/examples/causal/causal.cpp:103",
    "/home/jose/omnitrace/examples/causal/causal.cpp:110",
    "/home/jose/omnitrace/examples/causal/causal.cpp:112",
    "/usr/include/c++/9/bits/stl_vector.h:125",
    "/usr/include/c++/9/bits/stl_vector.h:128",
    "/usr/include/c++/9/bits/stl_vector.h:285",
    "/usr/include/c++/9/ext/string_conversions.h:83",
    "/usr/include/c++/9/ext/string_conversions.h:84",
    "/usr/include/c++/9/ext/string_conversions.h:85",
]

samples_df_expected_counts = [
    152,
    304,
    152,
    152,
    152,
    152,
    3648,
    456,
    760,
]

input_files = find_causal_files(
    [workload_dir], default_settings["verbose"], default_settings["recursive"]
)


def test_find_causal_files_valid_directory():
    file_names = [
        os.path.join(workload_dir, "experiments.json"),
        os.path.join(workload_dir, "experiments.coz"),
        os.path.join(workload_dir, "experiments3.json"),
        os.path.join(workload_dir, "experiments4.json"),
    ]
    file_names_recursive = [
        os.path.join(workload_dir, "experiments.json"),
        os.path.join(workload_dir, "experiments.coz"),
        os.path.join(workload_dir, *"part2/experiments2.json".split("/")),
        os.path.join(workload_dir, *"part2/experiments1.json".split("/")),
        os.path.join(workload_dir, "experiments3.json"),
        os.path.join(workload_dir, "experiments4.json"),
    ]

    # given a valid directory
    files_found = find_causal_files([workload_dir], default_settings["verbose"], False)
    assert len(files_found) == 4
    assert files_found == file_names

    # given invalid directory
    with pytest.raises(Exception) as e_info:
        find_causal_files(["nonsense"], default_settings["verbose"], False)

    # given valid directory with recursive
    files_found = find_causal_files([workload_dir], default_settings["verbose"], True)
    assert len(files_found) == 6
    assert files_found == file_names_recursive

    # given invalid directory with recursive
    with pytest.raises(Exception) as e_info:
        find_causal_files(["nonsense"], default_settings["verbose"], True)


def test_parse_files_default():
    file_names = [
        os.path.join(workload_dir, "experiments.json"),
        os.path.join(workload_dir, "experiments3.json"),
        os.path.join(workload_dir, "experiments4.json"),
    ]
    results_df_expected_impact_sum = np.full(4, -41.6965)
    results_df_expected_impact_avg = np.full(4, -13.8988)
    results_df_expected_impact_err = np.full(4, 3.6046)

    results_df, samples_df, file_names_run = parse_files(
        input_files,
        default_settings["experiments"],
        default_settings["progress_points"],
        [],
        0,
        [],
        default_settings["recursive"],
        default_settings["cli"],
    )

    top_df = results_df[
        results_df["idx"] == ("causal-cpu-omni", "cpu_fast_func(long, int)")
    ][:2]

    # sparse testing
    results_df_expected_program_speedup = [0.0, -1.7623]
    results_df_expected_speedup_err = [0.0264, 0.3931]
    results_df_expected_impact_sum = np.full(2, -41.6965)
    results_df_expected_impact_avg = np.full(2, -13.8988)
    results_df_expected_impact_err = np.full(2, 3.6046)
    results_df_expected_point_count = np.full(2, 4.0)

    assert file_names_run == file_names

    samples_df_locations = pd.concat(
        [samples_df[0:3], samples_df[100:103], samples_df[150:153]]
    )["location"].to_numpy()
    samples_df_counts = pd.concat(
        [samples_df[0:3], samples_df[100:103], samples_df[150:153]]
    )["count"].to_numpy()

    assert (samples_df_locations == samples_df_expected_locations).all()
    assert (samples_df_counts == samples_df_expected_counts).all()

    # assert expected speedup err
    assert (
        top_df["program speedup"].round(4).to_numpy()
        == results_df_expected_program_speedup
    ).all()

    # assert expected speedup err
    assert (
        top_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
    ).all()

    assert (
        top_df["impact sum"].round(4).to_numpy() == results_df_expected_impact_sum
    ).all()

    # assert expected impact avg
    assert (
        top_df["impact avg"].round(4).to_numpy() == results_df_expected_impact_avg
    ).all()

    # assert expected impact err
    assert (
        top_df["impact err"].round(4).to_numpy() == results_df_expected_impact_err
    ).all()

    # assert expected point count
    assert (
        top_df["point count"].round(4).to_numpy() == results_df_expected_point_count
    ).all()

    middle_df = results_df[
        results_df["idx"]
        == ("causal-cpu-omni", "/home/jose/omnitrace/examples/causal/causal.cpp:165")
    ][:2]

    results_df_expected_program_speedup = [0.0, -1.4123]
    results_df_expected_speedup_err = [0.0407, 0.2638]
    results_df_expected_impact_sum = np.full(2, -37.3877)
    results_df_expected_impact_avg = np.full(2, -12.4626)
    results_df_expected_impact_err = np.full(2, 3.8331)
    results_df_expected_point_count = np.full(2, 4.0)

    # assert expected speedup err
    assert (
        middle_df["program speedup"].round(4).to_numpy()
        == results_df_expected_program_speedup
    ).all()

    # assert expected speedup err
    assert (
        middle_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
    ).all()

    # assert exoected impact sum
    assert (
        middle_df["impact sum"].round(4).to_numpy() == results_df_expected_impact_sum
    ).all()

    # assert expected impact avg
    assert (
        middle_df["impact avg"].round(4).to_numpy() == results_df_expected_impact_avg
    ).all()

    # assert expected impact err
    assert (
        middle_df["impact err"].round(4).to_numpy() == results_df_expected_impact_err
    ).all()

    # assert expected point count
    assert (
        middle_df["point count"].round(4).to_numpy() == results_df_expected_point_count
    ).all()

    bottom_df = results_df[
        results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")
    ][:2]

    results_df_expected_program_speedup = [0.0, 10.3991]
    results_df_expected_speedup_err = [0.9115, 0.9072]
    results_df_expected_impact_sum = np.full(2, 385.195)
    results_df_expected_impact_avg = np.full(2, 128.3983)
    results_df_expected_impact_err = np.full(2, 56.9176)
    results_df_expected_point_count = np.full(2, 4.0)

    # assert expected speedup err
    assert (
        bottom_df["program speedup"].round(4).to_numpy()
        == results_df_expected_program_speedup
    ).all()

    # assert expected speedup err
    assert (
        bottom_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
    ).all()

    assert (
        results_df[results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")][
            "impact sum"
        ][:2]
        .round(4)
        .to_numpy()
        == results_df_expected_impact_sum
    ).all()

    # assert expected impact avg
    assert (
        results_df[results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")][
            "impact avg"
        ][:2]
        .round(4)
        .to_numpy()
        == results_df_expected_impact_avg
    ).all()

    # assert expected impact err
    assert (
        results_df[results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")][
            "impact err"
        ][:2]
        .round(4)
        .to_numpy()
        == results_df_expected_impact_err
    ).all()

    # assert expected point count
    assert (
        bottom_df["point count"][:2].round(4).to_numpy()
        == results_df_expected_point_count
    ).all()


def test_parse_files_valid_directory():
    # test given valid experiment
    file_names = [
        "/home/jose/omnitrace/omnitrace-build/omnitrace-tests-output/causal-cpu-omni-fast-func-e2e/causal/experiments.json"
    ]
    results_df, samples_df, file_names_run = parse_files(
        input_files,
        "fast",
        default_settings["progress_points"],
        [],
        0,
        [],
        default_settings["recursive"],
        default_settings["cli"],
    )

    top_df = results_df[
        results_df["idx"] == ("causal-cpu-omni", "cpu_fast_func(long, int)")
    ][:1]

    # sparse testing
    results_df_expected_program_speedup = [0.0]
    results_df_expected_speedup_err = [0.0264]
    results_df_expected_impact_sum = [-41.6965]
    results_df_expected_impact_avg = [-13.8988]
    results_df_expected_impact_err = [3.6046]
    results_df_expected_point_count = [4.0]

    assert file_names_run == file_names

    samples_df_locations = pd.concat(
        [samples_df[0:3], samples_df[100:103], samples_df[150:153]]
    )["location"].to_numpy()
    samples_df_counts = pd.concat(
        [samples_df[0:3], samples_df[100:103], samples_df[150:153]]
    )["count"].to_numpy()

    assert (samples_df_locations == samples_df_expected_locations).all()
    assert (samples_df_counts == samples_df_expected_counts).all()

    # assert expected speedup err
    assert (
        top_df["program speedup"].round(4).to_numpy()
        == results_df_expected_program_speedup
    ).all()

    # assert expected speedup err
    assert (
        top_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
    ).all()

    assert (
        top_df["impact sum"].round(4).to_numpy() == results_df_expected_impact_sum
    ).all()

    # assert expected impact avg
    assert (
        top_df["impact avg"].round(4).to_numpy() == results_df_expected_impact_avg
    ).all()

    # assert expected impact err
    assert (
        top_df["impact err"].round(4).to_numpy() == results_df_expected_impact_err
    ).all()

    # assert expected point count
    assert (
        top_df["point count"].round(4).to_numpy() == results_df_expected_point_count
    ).all()

    bottom_df = results_df[
        results_df["idx"] == ("causal-cpu-omni", "cpu_fast_func(long, int)")
    ][-1:]

    results_df_expected_program_speedup = [-1.6489]
    results_df_expected_speedup_err = [1.1804]
    results_df_expected_impact_sum = [-41.6965]
    results_df_expected_impact_avg = [-13.8988]
    results_df_expected_impact_err = [3.6046]
    results_df_expected_point_count = [4.0]

    # assert expected speedup err
    assert (
        bottom_df["program speedup"].round(4).to_numpy()
        == results_df_expected_program_speedup
    ).all()

    # assert expected speedup err
    assert (
        bottom_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
    ).all()

    assert (
        bottom_df["impact sum"].round(4).to_numpy() == results_df_expected_impact_sum
    ).all()

    # assert expected impact avg
    assert (
        bottom_df["impact avg"].round(4).to_numpy() == results_df_expected_impact_avg
    ).all()

    # assert expected impact err
    assert (
        bottom_df["impact err"].round(4).to_numpy() == results_df_expected_impact_err
    ).all()

    # assert expected point count
    assert bottom_df["point count"].round(4).to_numpy() == results_df_expected_point_count


def test_parse_files_invalid_experiment():
    ############################################################

    # test given invalid experiment
    results_df, samples_df, file_names_run = parse_files(
        input_files,
        "this_is_my_invalid_regex",
        default_settings["progress_points"],
        [],
        0,
        [],
        default_settings["recursive"],
        default_settings["cli"],
    )
    samples_df_expected_locations = [
        "0x00005555f6213863 :: /home/jose/omnitrace/examples/causal/causal.cpp:71",
        "0x00005555f62138e0 :: /home/jose/omnitrace/examples/causal/causal.cpp:71",
        "0x00005555f6213f1e :: _start",
        "0x00005600f87738e0 :: /home/jose/omnitrace/examples/causal/causal.cpp:71",
        "0x00005600f8773f1e :: _start",
        "0x000056075b7a6863 :: /home/jose/omnitrace/examples/causal/causal.cpp:71",
    ]

    file_names = [
        "/home/jose/omnitrace/omnitrace-build/omnitrace-tests-output/causal-cpu-omni-fast-func-e2e/causal/experiments.coz"
    ]

    samples_df_expected_counts = [4, 2, 6, 3, 4, 4]

    assert file_names_run == file_names
    samples_df_locations = pd.concat(
        [samples_df[0:3], samples_df[100:103], samples_df[150:153]]
    )["location"].to_numpy()
    samples_df_counts = pd.concat(
        [samples_df[0:3], samples_df[100:103], samples_df[150:153]]
    )["count"].to_numpy()

    assert (samples_df_locations == samples_df_expected_locations).all()
    assert (samples_df_counts == samples_df_expected_counts).all()

    results_df = results_df.round(4)
    # returns only .coz outputs since filtering is done in process_data
    expected_points = np.full(4, "cpu_fast_func(long, int)")
    expected_speedup = np.array([0.0, 10.0, 20.0, 30.0])
    expected_progress = np.array([0.0, -1.7623, -1.5829, -1.6489])

    assert (results_df["point"].to_numpy() == expected_points).all()

    assert (results_df["point"].to_numpy() == expected_points).all()
    assert (results_df["speedup"].to_numpy() == expected_speedup).all()
    assert (results_df["progress_speedup"].to_numpy() == expected_progress).all()


def test_parse_files_valid_progress_regex():
    file_names = [
        os.path.join(workload_dir, "experiments.json"),
        os.path.join(workload_dir, "experiments3.json"),
        os.path.join(workload_dir, "experiments4.json"),
    ]

    # test given valid progress_point regex
    results_df, samples_df, file_names_run = parse_files(
        input_files,
        default_settings["experiments"],
        "cpu",
        [],
        0,
        [],
        default_settings["recursive"],
        default_settings["cli"],
    )

    # sparse testing
    results_df_expected_program_speedup = [0.0, -1.7623]
    results_df_expected_speedup_err = [0.0264, 0.3931]
    results_df_expected_impact_sum = np.full(2, -41.6965)
    results_df_expected_impact_avg = np.full(2, -13.8988)
    results_df_expected_impact_err = np.full(2, 3.6046)
    results_df_expected_point_count = np.full(2, 4.0)

    top_df = results_df[
        results_df["idx"] == ("causal-cpu-omni", "cpu_fast_func(long, int)")
    ][:2]

    assert file_names_run == file_names

    samples_df_locations = pd.concat(
        [samples_df[0:3], samples_df[100:103], samples_df[150:153]]
    )["location"].to_numpy()
    samples_df_counts = pd.concat(
        [samples_df[0:3], samples_df[100:103], samples_df[150:153]]
    )["count"].to_numpy()

    samples_df_expected_counts = [152, 304, 152, 152, 152, 152, 3648, 456, 760]

    assert (samples_df_locations == samples_df_expected_locations).all()
    assert (samples_df_counts == samples_df_expected_counts).all()

    # assert expected speedup err
    assert (
        top_df["program speedup"].round(4).to_numpy()
        == results_df_expected_program_speedup
    ).all()

    # assert expected speedup err
    assert (
        top_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
    ).all()

    assert (
        top_df["impact sum"].round(4).to_numpy() == results_df_expected_impact_sum
    ).all()

    # assert expected impact avg
    assert (
        top_df["impact avg"].round(4).to_numpy() == results_df_expected_impact_avg
    ).all()

    # assert expected impact err
    assert (
        top_df["impact err"].round(4).to_numpy() == results_df_expected_impact_err
    ).all()

    # assert expected point count
    assert (
        top_df["point count"].round(4).to_numpy() == results_df_expected_point_count
    ).all()

    middle_df = results_df[
        results_df["idx"]
        == ("causal-cpu-omni", "/home/jose/omnitrace/examples/causal/causal.cpp:165")
    ][:2]

    results_df_expected_program_speedup = [0.0, -1.4123]
    results_df_expected_speedup_err = [0.0407, 0.2638]
    results_df_expected_impact_sum = np.full(2, -37.3877)
    results_df_expected_impact_avg = np.full(2, -12.4626)
    results_df_expected_impact_err = np.full(2, 3.8331)
    results_df_expected_point_count = np.full(2, 4.0)

    # assert expected speedup err
    assert (
        middle_df["program speedup"].round(4).to_numpy()
        == results_df_expected_program_speedup
    ).all()

    # assert expected speedup err
    assert (
        middle_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
    ).all()

    # assert exoected impact sum
    assert (
        middle_df["impact sum"].round(4).to_numpy() == results_df_expected_impact_sum
    ).all()

    # assert expected impact avg
    assert (
        middle_df["impact avg"].round(4).to_numpy() == results_df_expected_impact_avg
    ).all()

    # assert expected impact err
    assert (
        middle_df["impact err"].round(4).to_numpy() == results_df_expected_impact_err
    ).all()

    # assert expected point count
    assert (
        middle_df["point count"].round(4).to_numpy() == results_df_expected_point_count
    ).all()

    bottom_df = results_df[
        results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")
    ][:2]

    results_df_expected_program_speedup = [0.0, 10.3991]
    results_df_expected_speedup_err = [0.9115, 0.9072]
    results_df_expected_impact_sum = np.full(2, 385.195)
    results_df_expected_impact_avg = np.full(2, 128.3983)
    results_df_expected_impact_err = np.full(2, 56.9176)
    results_df_expected_point_count = np.full(2, 4.0)

    # assert expected speedup err
    assert (
        bottom_df["program speedup"].round(4).to_numpy()
        == results_df_expected_program_speedup
    ).all()

    # assert expected speedup err
    assert (
        bottom_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
    ).all()

    assert (
        results_df[results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")][
            "impact sum"
        ][:2]
        .round(4)
        .to_numpy()
        == results_df_expected_impact_sum
    ).all()

    # assert expected impact avg
    assert (
        results_df[results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")][
            "impact avg"
        ][:2]
        .round(4)
        .to_numpy()
        == results_df_expected_impact_avg
    ).all()

    # assert expected impact err
    assert (
        results_df[results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")][
            "impact err"
        ][:2]
        .round(4)
        .to_numpy()
        == results_df_expected_impact_err
    ).all()

    # assert expected point count
    assert (
        bottom_df["point count"][:2].round(4).to_numpy()
        == results_df_expected_point_count
    ).all()


def test_parse_files_invalid_progress_regex():
    # test given invalid progress_point regex
    results_df, samples_df, file_names_run = parse_files(
        input_files,
        default_settings["experiments"],
        "this_is_my_invalid_regex",
        [],
        0,
        [],
        default_settings["recursive"],
        default_settings["cli"],
    )

    samples_df_expected_locations = [
        "0x00005555f6213863 :: /home/jose/omnitrace/examples/causal/causal.cpp:71",
        "0x00005555f62138e0 :: /home/jose/omnitrace/examples/causal/causal.cpp:71",
        "0x00005555f6213f1e :: _start",
        "0x00005600f87738e0 :: /home/jose/omnitrace/examples/causal/causal.cpp:71",
        "0x00005600f8773f1e :: _start",
        "0x000056075b7a6863 :: /home/jose/omnitrace/examples/causal/causal.cpp:71",
    ]

    file_names = [
        "/home/jose/omnitrace/omnitrace-build/omnitrace-tests-output/causal-cpu-omni-fast-func-e2e/causal/experiments.coz"
    ]

    results_df = results_df.round(4)
    samples_df_locations = pd.concat(
        [samples_df[0:3], samples_df[100:103], samples_df[150:153]]
    )["location"].to_numpy()
    samples_df_counts = pd.concat(
        [samples_df[0:3], samples_df[100:103], samples_df[150:153]]
    )["count"].to_numpy()
    # returns only .coz outputs since filtering is done in process_data
    expected_points = np.full(4, "cpu_fast_func(long, int)")
    expected_speedup = np.array([0.0, 10.0, 20.0, 30.0])
    expected_progress = np.array([0.0, -1.7623, -1.5829, -1.6489])

    assert (results_df["point"].to_numpy() == expected_points).all()

    assert (results_df["point"].to_numpy() == expected_points).all()
    assert (results_df["speedup"].to_numpy() == expected_speedup).all()
    assert (results_df["progress_speedup"].to_numpy() == expected_progress).all()
    assert file_names_run == file_names
    assert (samples_df_locations == samples_df_expected_locations).all()


def test_parse_files_valid_speedup():
    file_names = [
        os.path.join(workload_dir, "experiments.json"),
        os.path.join(workload_dir, "experiments3.json"),
        os.path.join(workload_dir, "experiments4.json"),
    ]

    # test given valid speedup
    results_df, samples_df, file_names_run = parse_files(
        input_files,
        default_settings["experiments"],
        default_settings["progress_points"],
        [0, 10],
        0,
        [],
        default_settings["recursive"],
        default_settings["cli"],
    )

    top_df = results_df[
        results_df["idx"] == ("causal-cpu-omni", "cpu_fast_func(long, int)")
    ][:2]

    # sparse testing
    results_df_expected_program_speedup = [0.0, -1.7623]
    results_df_expected_speedup_err = [0.0264, 0.3931]
    results_df_expected_impact_sum = np.full(2, -8.8117)
    results_df_expected_impact_avg = np.full(2, -8.8117)
    results_df_expected_impact_err = np.full(2, 0)
    results_df_expected_point_count = np.full(2, 2.0)

    assert file_names_run == file_names

    samples_df_locations = pd.concat(
        [samples_df[0:3], samples_df[100:103], samples_df[150:153]]
    )["location"].to_numpy()
    samples_df_counts = pd.concat(
        [samples_df[0:3], samples_df[100:103], samples_df[150:153]]
    )["count"].to_numpy()

    assert (samples_df_locations == samples_df_expected_locations).all()
    assert (samples_df_counts == samples_df_expected_counts).all()

    # assert expected speedup err
    assert (
        top_df["program speedup"].round(4).to_numpy()
        == results_df_expected_program_speedup
    ).all()

    # assert expected speedup err
    assert (
        top_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
    ).all()

    assert (
        top_df["impact sum"].round(4).to_numpy() == results_df_expected_impact_sum
    ).all()

    # assert expected impact avg
    assert (
        top_df["impact avg"].round(4).to_numpy() == results_df_expected_impact_avg
    ).all()

    # assert expected impact err
    assert (
        top_df["impact err"].round(4).to_numpy() == results_df_expected_impact_err
    ).all()

    # assert expected point count
    assert (
        top_df["point count"].round(4).to_numpy() == results_df_expected_point_count
    ).all()

    middle_df = results_df[
        results_df["idx"]
        == ("causal-cpu-omni", "/home/jose/omnitrace/examples/causal/causal.cpp:165")
    ][:2]

    results_df_expected_program_speedup = [0.0, -1.4123]
    results_df_expected_speedup_err = [0.0407, 0.2638]
    results_df_expected_impact_sum = np.full(2, -7.0613)
    results_df_expected_impact_avg = np.full(2, -7.0613)
    results_df_expected_impact_err = np.full(2, 0)
    results_df_expected_point_count = np.full(2, 2.0)

    # assert expected speedup err
    assert (
        middle_df["program speedup"].round(4).to_numpy()
        == results_df_expected_program_speedup
    ).all()

    # assert expected speedup err
    assert (
        middle_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
    ).all()

    # assert exoected impact sum
    assert (
        middle_df["impact sum"].round(4).to_numpy() == results_df_expected_impact_sum
    ).all()

    # assert expected impact avg
    assert (
        middle_df["impact avg"].round(4).to_numpy() == results_df_expected_impact_avg
    ).all()

    # assert expected impact err
    assert (
        middle_df["impact err"].round(4).to_numpy() == results_df_expected_impact_err
    ).all()

    # assert expected point count
    assert (
        middle_df["point count"].round(4).to_numpy() == results_df_expected_point_count
    ).all()

    bottom_df = results_df[
        results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")
    ][:2]

    results_df_expected_program_speedup = [0.0, 10.3991]
    results_df_expected_speedup_err = [0.9115, 0.9072]
    results_df_expected_impact_sum = np.full(2, 51.9953)
    results_df_expected_impact_avg = np.full(2, 51.9953)
    results_df_expected_impact_err = np.full(2, 0)
    results_df_expected_point_count = np.full(2, 2.0)

    # assert expected speedup err
    assert (
        bottom_df["program speedup"].round(4).to_numpy()
        == results_df_expected_program_speedup
    ).all()

    # assert expected speedup err
    assert (
        bottom_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
    ).all()

    assert (
        results_df[results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")][
            "impact sum"
        ][:2]
        .round(4)
        .to_numpy()
        == results_df_expected_impact_sum
    ).all()

    # assert expected impact avg
    assert (
        results_df[results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")][
            "impact avg"
        ][:2]
        .round(4)
        .to_numpy()
        == results_df_expected_impact_avg
    ).all()

    # assert expected impact err
    assert (
        results_df[results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")][
            "impact err"
        ][:2]
        .round(4)
        .to_numpy()
        == results_df_expected_impact_err
    ).all()

    # assert expected point count
    assert (
        bottom_df["point count"][:2].round(4).to_numpy()
        == results_df_expected_point_count
    ).all()


def test_parse_files_invalid_speedup():
    # test given invalid speedup
    file_names = [
        os.path.join(workload_dir, "experiments.json"),
        os.path.join(workload_dir, "experiments3.json"),
        os.path.join(workload_dir, "experiments4.json"),
    ]

    results_df, samples_df, file_names_run = parse_files(
        input_files,
        default_settings["experiments"],
        default_settings["progress_points"],
        [12, 14],
        0,
        [],
        default_settings["recursive"],
        default_settings["cli"],
    )

    assert file_names_run == file_names

    samples_df_locations = pd.concat(
        [samples_df[0:3], samples_df[100:103], samples_df[150:153]]
    )["location"].to_numpy()
    samples_df_counts = pd.concat(
        [samples_df[0:3], samples_df[100:103], samples_df[150:153]]
    )["count"].to_numpy()

    assert (samples_df_locations == samples_df_expected_locations).all()
    assert (samples_df_counts == samples_df_expected_counts).all()

    assert results_df.empty


def test_parse_files_valid_min_points():
    file_names = [
        os.path.join(workload_dir, "experiments.json"),
        os.path.join(workload_dir, "experiments3.json"),
        os.path.join(workload_dir, "experiments4.json"),
    ]

    ##############################################################################################
    # test given valid min points
    results_df, samples_df, file_names_run = parse_files(
        input_files,
        default_settings["experiments"],
        default_settings["progress_points"],
        [],
        1,
        [],
        default_settings["recursive"],
        default_settings["cli"],
    )

    top_df = results_df[
        results_df["idx"] == ("causal-cpu-omni", "cpu_fast_func(long, int)")
    ][:2]

    # sparse testing
    results_df_expected_program_speedup = [0.0, -1.7623]
    results_df_expected_speedup_err = [0.0264, 0.3931]
    results_df_expected_impact_sum = np.full(2, -41.6965)
    results_df_expected_impact_avg = np.full(2, -13.8988)
    results_df_expected_impact_err = np.full(2, 3.6046)
    results_df_expected_point_count = np.full(2, 4.0)

    assert file_names_run == file_names

    samples_df_locations = pd.concat(
        [samples_df[0:3], samples_df[100:103], samples_df[150:153]]
    )["location"].to_numpy()
    samples_df_counts = pd.concat(
        [samples_df[0:3], samples_df[100:103], samples_df[150:153]]
    )["count"].to_numpy()

    assert (samples_df_locations == samples_df_expected_locations).all()
    assert (samples_df_counts == samples_df_expected_counts).all()

    # assert expected speedup err
    assert (
        top_df["program speedup"].round(4).to_numpy()
        == results_df_expected_program_speedup
    ).all()

    # assert expected speedup err
    assert (
        top_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
    ).all()

    assert (
        top_df["impact sum"].round(4).to_numpy() == results_df_expected_impact_sum
    ).all()

    # assert expected impact avg
    assert (
        top_df["impact avg"].round(4).to_numpy() == results_df_expected_impact_avg
    ).all()

    # assert expected impact err
    assert (
        top_df["impact err"].round(4).to_numpy() == results_df_expected_impact_err
    ).all()

    # assert expected point count
    assert (
        top_df["point count"].round(4).to_numpy() == results_df_expected_point_count
    ).all()

    middle_df = results_df[
        results_df["idx"]
        == ("causal-cpu-omni", "/home/jose/omnitrace/examples/causal/causal.cpp:165")
    ][:2]

    results_df_expected_program_speedup = [0.0, -1.4123]
    results_df_expected_speedup_err = [0.0407, 0.2638]
    results_df_expected_impact_sum = np.full(2, -37.3877)
    results_df_expected_impact_avg = np.full(2, -12.4626)
    results_df_expected_impact_err = np.full(2, 3.8331)
    results_df_expected_point_count = np.full(2, 4.0)

    # assert expected speedup err
    assert (
        middle_df["program speedup"].round(4).to_numpy()
        == results_df_expected_program_speedup
    ).all()

    # assert expected speedup err
    assert (
        middle_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
    ).all()

    # assert exoected impact sum
    assert (
        middle_df["impact sum"].round(4).to_numpy() == results_df_expected_impact_sum
    ).all()

    # assert expected impact avg
    assert (
        middle_df["impact avg"].round(4).to_numpy() == results_df_expected_impact_avg
    ).all()

    # assert expected impact err
    assert (
        middle_df["impact err"].round(4).to_numpy() == results_df_expected_impact_err
    ).all()

    # assert expected point count
    assert (
        middle_df["point count"].round(4).to_numpy() == results_df_expected_point_count
    ).all()

    bottom_df = results_df[
        results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")
    ][:2]

    results_df_expected_program_speedup = [0.0, 10.3991]
    results_df_expected_speedup_err = [0.9115, 0.9072]
    results_df_expected_impact_sum = np.full(2, 385.195)
    results_df_expected_impact_avg = np.full(2, 128.3983)
    results_df_expected_impact_err = np.full(2, 56.9176)
    results_df_expected_point_count = np.full(2, 4.0)

    # assert expected speedup err
    assert (
        bottom_df["program speedup"].round(4).to_numpy()
        == results_df_expected_program_speedup
    ).all()

    # assert expected speedup err
    assert (
        bottom_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
    ).all()

    assert (
        results_df[results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")][
            "impact sum"
        ][:2]
        .round(4)
        .to_numpy()
        == results_df_expected_impact_sum
    ).all()

    # assert expected impact avg
    assert (
        results_df[results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")][
            "impact avg"
        ][:2]
        .round(4)
        .to_numpy()
        == results_df_expected_impact_avg
    ).all()

    # assert expected impact err
    assert (
        results_df[results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")][
            "impact err"
        ][:2]
        .round(4)
        .to_numpy()
        == results_df_expected_impact_err
    ).all()

    # assert expected point count
    assert (
        bottom_df["point count"][:2].round(4).to_numpy()
        == results_df_expected_point_count
    ).all()


def test_parse_files_high_min_points():
    file_names = [
        os.path.join(workload_dir, "experiments.json"),
        os.path.join(workload_dir, "experiments3.json"),
        os.path.join(workload_dir, "experiments4.json"),
    ]
    ###################################################################################
    # test given too high min points
    results_df, samples_df, file_names_run = parse_files(
        input_files,
        default_settings["experiments"],
        default_settings["progress_points"],
        [],
        1000,
        [],
        default_settings["recursive"],
        default_settings["cli"],
    )
    top_df = results_df[
        results_df["idx"] == ("causal-cpu-omni", "cpu_fast_func(long, int)")
    ][:2]

    # sparse testing
    results_df_expected_program_speedup = [0.0, -1.7623]
    results_df_expected_speedup_err = [0.0264, 0.3931]
    results_df_expected_impact_sum = np.full(2, -41.6965)
    results_df_expected_impact_avg = np.full(2, -13.8988)
    results_df_expected_impact_err = np.full(2, 3.6046)
    results_df_expected_point_count = np.full(2, 4.0)

    assert file_names_run == file_names

    samples_df_locations = pd.concat(
        [samples_df[0:3], samples_df[100:103], samples_df[150:153]]
    )["location"].to_numpy()
    samples_df_counts = pd.concat(
        [samples_df[0:3], samples_df[100:103], samples_df[150:153]]
    )["count"].to_numpy()

    assert (samples_df_locations == samples_df_expected_locations).all()
    assert (samples_df_counts == samples_df_expected_counts).all()

    # assert expected speedup err
    assert (
        top_df["program speedup"].round(4).to_numpy()
        == results_df_expected_program_speedup
    ).all()

    # assert expected speedup err
    assert (
        top_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
    ).all()

    assert (
        top_df["impact sum"].round(4).to_numpy() == results_df_expected_impact_sum
    ).all()

    # assert expected impact avg
    assert (
        top_df["impact avg"].round(4).to_numpy() == results_df_expected_impact_avg
    ).all()

    # assert expected impact err
    assert (
        top_df["impact err"].round(4).to_numpy() == results_df_expected_impact_err
    ).all()

    # assert expected point count
    assert (
        top_df["point count"].round(4).to_numpy() == results_df_expected_point_count
    ).all()

    middle_df = results_df[
        results_df["idx"]
        == ("causal-cpu-omni", "/home/jose/omnitrace/examples/causal/causal.cpp:165")
    ][:2]

    results_df_expected_program_speedup = [0.0, -1.4123]
    results_df_expected_speedup_err = [0.0407, 0.2638]
    results_df_expected_impact_sum = np.full(2, -37.3877)
    results_df_expected_impact_avg = np.full(2, -12.4626)
    results_df_expected_impact_err = np.full(2, 3.8331)
    results_df_expected_point_count = np.full(2, 4.0)

    # assert expected speedup err
    assert (
        middle_df["program speedup"].round(4).to_numpy()
        == results_df_expected_program_speedup
    ).all()

    # assert expected speedup err
    assert (
        middle_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
    ).all()

    # assert exoected impact sum
    assert (
        middle_df["impact sum"].round(4).to_numpy() == results_df_expected_impact_sum
    ).all()

    # assert expected impact avg
    assert (
        middle_df["impact avg"].round(4).to_numpy() == results_df_expected_impact_avg
    ).all()

    # assert expected impact err
    assert (
        middle_df["impact err"].round(4).to_numpy() == results_df_expected_impact_err
    ).all()

    # assert expected point count
    assert (
        middle_df["point count"].round(4).to_numpy() == results_df_expected_point_count
    ).all()

    bottom_df = results_df[
        results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")
    ][:2]

    results_df_expected_program_speedup = [0.0, 10.3991]
    results_df_expected_speedup_err = [0.9115, 0.9072]
    results_df_expected_impact_sum = np.full(2, 385.195)
    results_df_expected_impact_avg = np.full(2, 128.3983)
    results_df_expected_impact_err = np.full(2, 56.9176)
    results_df_expected_point_count = np.full(2, 4.0)

    # assert expected speedup err
    assert (
        bottom_df["program speedup"].round(4).to_numpy()
        == results_df_expected_program_speedup
    ).all()

    # assert expected speedup err
    assert (
        bottom_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
    ).all()

    assert (
        results_df[results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")][
            "impact sum"
        ][:2]
        .round(4)
        .to_numpy()
        == results_df_expected_impact_sum
    ).all()

    # assert expected impact avg
    assert (
        results_df[results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")][
            "impact avg"
        ][:2]
        .round(4)
        .to_numpy()
        == results_df_expected_impact_avg
    ).all()

    # assert expected impact err
    assert (
        results_df[results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")][
            "impact err"
        ][:2]
        .round(4)
        .to_numpy()
        == results_df_expected_impact_err
    ).all()

    # assert expected point count
    assert (
        bottom_df["point count"][:2].round(4).to_numpy()
        == results_df_expected_point_count
    ).all()


def test_parse_files_validation():
    file_names = [
        os.path.join(workload_dir, "experiments.json"),
        os.path.join(workload_dir, "experiments3.json"),
        os.path.join(workload_dir, "experiments4.json"),
    ]

    ##################################################################################################
    # test given valid validation
    results_df, samples_df, file_names_run = parse_files(
        input_files,
        default_settings["experiments"],
        default_settings["progress_points"],
        [],
        0,
        ["fast", ".*", "10", "-2", "1"],
        default_settings["recursive"],
        default_settings["cli"],
    )

    top_df = results_df[
        results_df["idx"] == ("causal-cpu-omni", "cpu_fast_func(long, int)")
    ][:2]

    # sparse testing
    results_df_expected_program_speedup = [0.0, -1.7623]
    results_df_expected_speedup_err = [0.0264, 0.3931]
    results_df_expected_impact_sum = np.full(2, -41.6965)
    results_df_expected_impact_avg = np.full(2, -13.8988)
    results_df_expected_impact_err = np.full(2, 3.6046)
    results_df_expected_point_count = np.full(2, 4.0)

    assert file_names_run == file_names

    samples_df_locations = pd.concat(
        [samples_df[0:3], samples_df[100:103], samples_df[150:153]]
    )["location"].to_numpy()
    samples_df_counts = pd.concat(
        [samples_df[0:3], samples_df[100:103], samples_df[150:153]]
    )["count"].to_numpy()

    assert (samples_df_locations == samples_df_expected_locations).all()
    assert (samples_df_counts == samples_df_expected_counts).all()

    # assert expected speedup err
    assert (
        top_df["program speedup"].round(4).to_numpy()
        == results_df_expected_program_speedup
    ).all()

    # assert expected speedup err
    assert (
        top_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
    ).all()

    assert (
        top_df["impact sum"].round(4).to_numpy() == results_df_expected_impact_sum
    ).all()

    # assert expected impact avg
    assert (
        top_df["impact avg"].round(4).to_numpy() == results_df_expected_impact_avg
    ).all()

    # assert expected impact err
    assert (
        top_df["impact err"].round(4).to_numpy() == results_df_expected_impact_err
    ).all()

    # assert expected point count
    assert (
        top_df["point count"].round(4).to_numpy() == results_df_expected_point_count
    ).all()

    middle_df = results_df[
        results_df["idx"]
        == ("causal-cpu-omni", "/home/jose/omnitrace/examples/causal/causal.cpp:165")
    ][:2]

    results_df_expected_program_speedup = [0.0, -1.4123]
    results_df_expected_speedup_err = [0.0407, 0.2638]
    results_df_expected_impact_sum = np.full(2, -37.3877)
    results_df_expected_impact_avg = np.full(2, -12.4626)
    results_df_expected_impact_err = np.full(2, 3.8331)
    results_df_expected_point_count = np.full(2, 4.0)

    # assert expected speedup err
    assert (
        middle_df["program speedup"].round(4).to_numpy()
        == results_df_expected_program_speedup
    ).all()

    # assert expected speedup err
    assert (
        middle_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
    ).all()

    # assert exoected impact sum
    assert (
        middle_df["impact sum"].round(4).to_numpy() == results_df_expected_impact_sum
    ).all()

    # assert expected impact avg
    assert (
        middle_df["impact avg"].round(4).to_numpy() == results_df_expected_impact_avg
    ).all()

    # assert expected impact err
    assert (
        middle_df["impact err"].round(4).to_numpy() == results_df_expected_impact_err
    ).all()

    # assert expected point count
    assert (
        middle_df["point count"].round(4).to_numpy() == results_df_expected_point_count
    ).all()

    bottom_df = results_df[
        results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")
    ][:2]

    results_df_expected_program_speedup = [0.0, 10.3991]
    results_df_expected_speedup_err = [0.9115, 0.9072]
    results_df_expected_impact_sum = np.full(2, 385.195)
    results_df_expected_impact_avg = np.full(2, 128.3983)
    results_df_expected_impact_err = np.full(2, 56.9176)
    results_df_expected_point_count = np.full(2, 4.0)

    # assert expected speedup err
    assert (
        bottom_df["program speedup"].round(4).to_numpy()
        == results_df_expected_program_speedup
    ).all()

    # assert expected speedup err
    assert (
        bottom_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
    ).all()

    assert (
        results_df[results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")][
            "impact sum"
        ][:2]
        .round(4)
        .to_numpy()
        == results_df_expected_impact_sum
    ).all()

    # assert expected impact avg
    assert (
        results_df[results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")][
            "impact avg"
        ][:2]
        .round(4)
        .to_numpy()
        == results_df_expected_impact_avg
    ).all()

    # assert expected impact err
    assert (
        results_df[results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")][
            "impact err"
        ][:2]
        .round(4)
        .to_numpy()
        == results_df_expected_impact_err
    ).all()

    # assert expected point count
    assert (
        bottom_df["point count"][:2].round(4).to_numpy()
        == results_df_expected_point_count
    ).all()

    # test given invalid validation
    results_df, samples_df_, file_names_run = parse_files(
        input_files,
        default_settings["experiments"],
        default_settings["progress_points"],
        [],
        0,
        ["fast", "fast", "12", "1024", "0"],
        default_settings["recursive"],
        default_settings["cli"],
    )

    top_df = results_df[
        results_df["idx"] == ("causal-cpu-omni", "cpu_fast_func(long, int)")
    ][:2]

    # sparse testing
    results_df_expected_program_speedup = [0.0, -1.7623]
    results_df_expected_speedup_err = [0.0264, 0.3931]
    results_df_expected_impact_sum = np.full(2, -41.6965)
    results_df_expected_impact_avg = np.full(2, -13.8988)
    results_df_expected_impact_err = np.full(2, 3.6046)
    results_df_expected_point_count = np.full(2, 4.0)

    assert file_names_run == file_names

    samples_df_locations = pd.concat(
        [samples_df[0:3], samples_df[100:103], samples_df[150:153]]
    )["location"].to_numpy()
    samples_df_counts = pd.concat(
        [samples_df[0:3], samples_df[100:103], samples_df[150:153]]
    )["count"].to_numpy()

    assert (samples_df_locations == samples_df_expected_locations).all()
    assert (samples_df_counts == samples_df_expected_counts).all()

    # assert expected speedup err
    assert (
        top_df["program speedup"].round(4).to_numpy()
        == results_df_expected_program_speedup
    ).all()

    # assert expected speedup err
    assert (
        top_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
    ).all()

    assert (
        top_df["impact sum"].round(4).to_numpy() == results_df_expected_impact_sum
    ).all()

    # assert expected impact avg
    assert (
        top_df["impact avg"].round(4).to_numpy() == results_df_expected_impact_avg
    ).all()

    # assert expected impact err
    assert (
        top_df["impact err"].round(4).to_numpy() == results_df_expected_impact_err
    ).all()

    # assert expected point count
    assert (
        top_df["point count"].round(4).to_numpy() == results_df_expected_point_count
    ).all()

    middle_df = results_df[
        results_df["idx"]
        == ("causal-cpu-omni", "/home/jose/omnitrace/examples/causal/causal.cpp:165")
    ][:2]

    results_df_expected_program_speedup = [0.0, -1.4123]
    results_df_expected_speedup_err = [0.0407, 0.2638]
    results_df_expected_impact_sum = np.full(2, -37.3877)
    results_df_expected_impact_avg = np.full(2, -12.4626)
    results_df_expected_impact_err = np.full(2, 3.8331)
    results_df_expected_point_count = np.full(2, 4.0)

    # assert expected speedup err
    assert (
        middle_df["program speedup"].round(4).to_numpy()
        == results_df_expected_program_speedup
    ).all()

    # assert expected speedup err
    assert (
        middle_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
    ).all()

    # assert exoected impact sum
    assert (
        middle_df["impact sum"].round(4).to_numpy() == results_df_expected_impact_sum
    ).all()

    # assert expected impact avg
    assert (
        middle_df["impact avg"].round(4).to_numpy() == results_df_expected_impact_avg
    ).all()

    # assert expected impact err
    assert (
        middle_df["impact err"].round(4).to_numpy() == results_df_expected_impact_err
    ).all()

    # assert expected point count
    assert (
        middle_df["point count"].round(4).to_numpy() == results_df_expected_point_count
    ).all()

    bottom_df = results_df[
        results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")
    ][:2]

    results_df_expected_program_speedup = [0.0, 10.3991]
    results_df_expected_speedup_err = [0.9115, 0.9072]
    results_df_expected_impact_sum = np.full(2, 385.195)
    results_df_expected_impact_avg = np.full(2, 128.3983)
    results_df_expected_impact_err = np.full(2, 56.9176)
    results_df_expected_point_count = np.full(2, 4.0)

    # assert expected speedup err
    assert (
        bottom_df["program speedup"].round(4).to_numpy()
        == results_df_expected_program_speedup
    ).all()

    # assert expected speedup err
    assert (
        bottom_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
    ).all()

    assert (
        results_df[results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")][
            "impact sum"
        ][:2]
        .round(4)
        .to_numpy()
        == results_df_expected_impact_sum
    ).all()

    # assert expected impact avg
    assert (
        results_df[results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")][
            "impact avg"
        ][:2]
        .round(4)
        .to_numpy()
        == results_df_expected_impact_avg
    ).all()

    # assert expected impact err
    assert (
        results_df[results_df["idx"] == ("causal-cpu-omni", "cpu_slow_func(long, int)")][
            "impact err"
        ][:2]
        .round(4)
        .to_numpy()
        == results_df_expected_impact_err
    ).all()

    # assert expected point count
    assert (
        bottom_df["point count"][:2].round(4).to_numpy()
        == results_df_expected_point_count
    ).all()


def test_parse_files_invalid_validation():
    # test given invalid validation len
    with pytest.raises(Exception) as e_info:
        parse_files(
            input_files,
            default_settings["experiments"],
            default_settings["progress_points"],
            [],
            0,
            ["fast", "fast", "12", "1024", "0", "10"],
            default_settings["recursive"],
            default_settings["cli"],
        )


def test_set_num_stddev():
    assert True


def test_process_data():
    # test with valid data
    with open(os.path.join(workload_dir, "experiments.json")) as file:
        _data = json.loads(file.read())
        dict_data = {}
        data = process_data(dict_data, _data, ".*", ".*")
        assert list(dict_data.keys()) == ["cpu_fast_func(long, int)"]
        assert list(data.keys()) == ["cpu_fast_func(long, int)"]

        data = process_data({}, _data, ".*", "fast")
        assert list(dict_data.keys()) == ["cpu_fast_func(long, int)"]
        assert list(data.keys()) == []

        data = process_data({}, _data, "fast", ".*")
        assert list(dict_data.keys()) == ["cpu_fast_func(long, int)"]
        assert list(data.keys()) == ["cpu_fast_func(long, int)"]

        data = process_data({}, _data, ".*", "impl")
        assert list(dict_data.keys()) == ["cpu_fast_func(long, int)"]
        assert list(data.keys()) == []

        data = process_data({}, _data, "impl", ".*")
        assert list(dict_data.keys()) == ["cpu_fast_func(long, int)"]
        assert list(data.keys()) == []

    assert True


def test_compute_speedups_verb_1():
    with open(os.path.join(workload_dir, "experiments.json")) as file:
        _data = json.loads(file.read())

        dict_data = {}
        dict_data[os.path.join(workload_dir, "experiments.json")] = process_data(
            {}, _data, ".*", ".*"
        )

        # Testing verbosity
        results_df = compute_speedups(
            dict_data, [], default_settings["min_points"], [], 3
        )

        top_df = results_df[
            results_df["idx"] == ("causal-cpu-omni", "cpu_fast_func(long, int)")
        ][:2]

        # sparse testing
        results_df_expected_program_speedup = [0.0, -1.7623]
        results_df_expected_speedup_err = [0.0264, 0.3931]
        results_df_expected_impact_sum = np.full(2, -41.6965)
        results_df_expected_impact_avg = np.full(2, -13.8988)
        results_df_expected_impact_err = np.full(2, 3.6046)

        # assert expected speedup err
        assert (
            top_df["program speedup"].round(4).to_numpy()
            == results_df_expected_program_speedup
        ).all()

        # assert expected speedup err
        assert (
            top_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
        ).all()

        assert (
            top_df["impact sum"].round(4).to_numpy() == results_df_expected_impact_sum
        ).all()

        # assert expected impact avg
        assert (
            top_df["impact avg"].round(4).to_numpy() == results_df_expected_impact_avg
        ).all()

        # assert expected impact err
        assert (
            top_df["impact err"].round(4).to_numpy() == results_df_expected_impact_err
        ).all()


def test_compute_speedups_verb_2():
    with open(os.path.join(workload_dir, "experiments.json")) as file:
        _data = json.loads(file.read())

        dict_data = {}
        dict_data[os.path.join(workload_dir, "experiments.json")] = process_data(
            {}, _data, ".*", ".*"
        )
        # Testing verbosity
        results_df = compute_speedups(
            dict_data, [], default_settings["min_points"], [], 2
        )
        top_df = results_df[
            results_df["idx"] == ("causal-cpu-omni", "cpu_fast_func(long, int)")
        ][:2]

        # sparse testing
        results_df_expected_program_speedup = [0.0, -1.7623]
        results_df_expected_speedup_err = [0.0264, 0.3931]
        results_df_expected_impact_sum = np.full(2, -41.6965)
        results_df_expected_impact_avg = np.full(2, -13.8988)
        results_df_expected_impact_err = np.full(2, 3.6046)

        # assert expected speedup err
        assert (
            top_df["program speedup"].round(4).to_numpy()
            == results_df_expected_program_speedup
        ).all()

        # assert expected speedup err
        assert (
            top_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
        ).all()

        assert (
            top_df["impact sum"].round(4).to_numpy() == results_df_expected_impact_sum
        ).all()

        # assert expected impact avg
        assert (
            top_df["impact avg"].round(4).to_numpy() == results_df_expected_impact_avg
        ).all()

        # assert expected impact err
        assert (
            top_df["impact err"].round(4).to_numpy() == results_df_expected_impact_err
        ).all()


def test_compute_speedups_verb_1():
    with open(os.path.join(workload_dir, "experiments.json")) as file:
        _data = json.loads(file.read())

        dict_data = {}
        dict_data[os.path.join(workload_dir, "experiments.json")] = process_data(
            {}, _data, ".*", ".*"
        )
        # Testing verbosity
        results_df = compute_speedups(
            dict_data, [], default_settings["min_points"], [], 1
        )

        print(results_df)
        top_df = results_df[
            results_df["idx"] == ("causal-cpu-omni", "cpu_fast_func(long, int)")
        ][:2]

        # sparse testing
        results_df_expected_program_speedup = [0.0, -1.7623]
        results_df_expected_speedup_err = [0.0264, 0.3931]
        results_df_expected_impact_sum = np.full(2, -41.6965)
        results_df_expected_impact_avg = np.full(2, -13.8988)
        results_df_expected_impact_err = np.full(2, 3.6046)

        # assert expected speedup err
        assert (
            top_df["program speedup"].round(4).to_numpy()
            == results_df_expected_program_speedup
        ).all()

        # assert expected speedup err
        assert (
            top_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
        ).all()

        assert (
            top_df["impact sum"].round(4).to_numpy() == results_df_expected_impact_sum
        ).all()

        # assert expected impact avg
        assert (
            top_df["impact avg"].round(4).to_numpy() == results_df_expected_impact_avg
        ).all()

        # assert expected impact err
        assert (
            top_df["impact err"].round(4).to_numpy() == results_df_expected_impact_err
        ).all()


def test_compute_speedups_verb_0():
    with open(os.path.join(workload_dir, "experiments.json")) as file:
        _data = json.loads(file.read())

        dict_data = {}
        dict_data[os.path.join(workload_dir, "experiments.json")] = process_data(
            {}, _data, ".*", ".*"
        )

        # Testing verbosity
        results_df = compute_speedups(
            dict_data, [], default_settings["min_points"], [], 0
        )

        top_df = results_df[
            results_df["idx"] == ("causal-cpu-omni", "cpu_fast_func(long, int)")
        ][:2]

        # sparse testing
        results_df_expected_program_speedup = [0.0, -1.7623]
        results_df_expected_speedup_err = [0.0264, 0.3931]
        results_df_expected_impact_sum = np.full(2, -41.6965)
        results_df_expected_impact_avg = np.full(2, -13.8988)
        results_df_expected_impact_err = np.full(2, 3.6046)

        # assert expected speedup err
        assert (
            top_df["program speedup"].round(4).to_numpy()
            == results_df_expected_program_speedup
        ).all()

        # assert expected speedup err
        assert (
            top_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
        ).all()

        assert (
            top_df["impact sum"].round(4).to_numpy() == results_df_expected_impact_sum
        ).all()

        # assert expected impact avg
        assert (
            top_df["impact avg"].round(4).to_numpy() == results_df_expected_impact_avg
        ).all()

        # assert expected impact err
        assert (
            top_df["impact err"].round(4).to_numpy() == results_df_expected_impact_err
        ).all()


def test_compute_speedups_verb_4():
    with open(os.path.join(workload_dir, "experiments.json")) as file:
        _data = json.loads(file.read())

        dict_data = {}
        dict_data[os.path.join(workload_dir, "experiments.json")] = process_data(
            {}, _data, ".*", ".*"
        )
        # Testing verbosity
        results_df = compute_speedups(
            dict_data, [], default_settings["min_points"], [], 4
        )

        top_df = results_df[
            results_df["idx"] == ("causal-cpu-omni", "cpu_fast_func(long, int)")
        ][:2]

        # sparse testing
        results_df_expected_program_speedup = [0.0, -1.7623]
        results_df_expected_speedup_err = [0.0264, 0.3931]
        results_df_expected_impact_sum = np.full(2, -41.6965)
        results_df_expected_impact_avg = np.full(2, -13.8988)
        results_df_expected_impact_err = np.full(2, 3.6046)

        # assert expected speedup err
        assert (
            top_df["program speedup"].round(4).to_numpy()
            == results_df_expected_program_speedup
        ).all()

        # assert expected speedup err
        assert (
            top_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
        ).all()

        assert (
            top_df["impact sum"].round(4).to_numpy() == results_df_expected_impact_sum
        ).all()

        # assert expected impact avg
        assert (
            top_df["impact avg"].round(4).to_numpy() == results_df_expected_impact_avg
        ).all()

        # assert expected impact err
        assert (
            top_df["impact err"].round(4).to_numpy() == results_df_expected_impact_err
        ).all()


def test_compute_speedups_high_min_points():
    with open(os.path.join(workload_dir, "experiments.json")) as file:
        _data = json.loads(file.read())

        dict_data = {}
        dict_data[os.path.join(workload_dir, "experiments.json")] = process_data(
            {}, _data, ".*", ".*"
        )
        # min points too high
        results_df = compute_speedups(dict_data, [], 247, [], 3)

        top_df = results_df[
            results_df["idx"] == ("causal-cpu-omni", "cpu_fast_func(long, int)")
        ][:2]

        # sparse testing
        results_df_expected_program_speedup = [0.0, -1.7623]
        results_df_expected_speedup_err = [0.0264, 0.3931]
        results_df_expected_impact_sum = np.full(2, -41.6965)
        results_df_expected_impact_avg = np.full(2, -13.8988)
        results_df_expected_impact_err = np.full(2, 3.6046)

        # assert expected speedup err
        assert (
            top_df["program speedup"].round(4).to_numpy()
            == results_df_expected_program_speedup
        ).all()

        # assert expected speedup err
        assert (
            top_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
        ).all()

        assert (
            top_df["impact sum"].round(4).to_numpy() == results_df_expected_impact_sum
        ).all()

        # assert expected impact avg
        assert (
            top_df["impact avg"].round(4).to_numpy() == results_df_expected_impact_avg
        ).all()

        # assert expected impact err
        assert (
            top_df["impact err"].round(4).to_numpy() == results_df_expected_impact_err
        ).all()


def test_compute_speedups_min_points_0():
    with open(os.path.join(workload_dir, "experiments.json")) as file:
        _data = json.loads(file.read())

        dict_data = {}
        dict_data[os.path.join(workload_dir, "experiments.json")] = process_data(
            {}, _data, ".*", ".*"
        )
        # min points 0
        results_df = compute_speedups(dict_data, [], 0, [], 3)

        top_df = results_df[
            results_df["idx"] == ("causal-cpu-omni", "cpu_fast_func(long, int)")
        ][:2]

        # sparse testing
        results_df_expected_program_speedup = [0.0, -1.7623]
        results_df_expected_speedup_err = [0.0264, 0.3931]
        results_df_expected_impact_sum = np.full(2, -41.6965)
        results_df_expected_impact_avg = np.full(2, -13.8988)
        results_df_expected_impact_err = np.full(2, 3.6046)

        # assert expected speedup err
        assert (
            top_df["program speedup"].round(4).to_numpy()
            == results_df_expected_program_speedup
        ).all()

        # assert expected speedup err
        assert (
            top_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
        ).all()

        assert (
            top_df["impact sum"].round(4).to_numpy() == results_df_expected_impact_sum
        ).all()

        # assert expected impact avg
        assert (
            top_df["impact avg"].round(4).to_numpy() == results_df_expected_impact_avg
        ).all()

        # assert expected impact err
        assert (
            top_df["impact err"].round(4).to_numpy() == results_df_expected_impact_err
        ).all()


def test_compute_speedups_min_points_1():
    with open(os.path.join(workload_dir, "experiments.json")) as file:
        _data = json.loads(file.read())

        dict_data = {}
        dict_data[os.path.join(workload_dir, "experiments.json")] = process_data(
            {}, _data, ".*", ".*"
        )
        # min points 1
        results_df = compute_speedups(dict_data, [], 1, [], 3)
        top_df = results_df[
            results_df["idx"] == ("causal-cpu-omni", "cpu_fast_func(long, int)")
        ][:2]

        # sparse testing
        results_df_expected_program_speedup = [0.0, -1.7623]
        results_df_expected_speedup_err = [0.0264, 0.3931]
        results_df_expected_impact_sum = np.full(2, -41.6965)
        results_df_expected_impact_avg = np.full(2, -13.8988)
        results_df_expected_impact_err = np.full(2, 3.6046)

        # assert expected speedup err
        assert (
            top_df["program speedup"].round(4).to_numpy()
            == results_df_expected_program_speedup
        ).all()

        # assert expected speedup err
        assert (
            top_df["speedup err"].round(4).to_numpy() == results_df_expected_speedup_err
        ).all()

        assert (
            top_df["impact sum"].round(4).to_numpy() == results_df_expected_impact_sum
        ).all()

        # assert expected impact avg
        assert (
            top_df["impact avg"].round(4).to_numpy() == results_df_expected_impact_avg
        ).all()

        # assert expected impact err
        assert (
            top_df["impact err"].round(4).to_numpy() == results_df_expected_impact_err
        ).all()


def test_compute_speedups_empty_dict():
    with open(os.path.join(workload_dir, "experiments.json")) as file:
        _data = json.loads(file.read())

        dict_data = {}
        dict_data[os.path.join(workload_dir, "experiments.json")] = process_data(
            {}, _data, ".*", ".*"
        )
        # empty dict_data
        results_df = compute_speedups({}, [], 0, [], 3)
        assert results_df.empty


def test_get_validations():
    assert True


def test_compute_sorts():
    assert True


def test_parse_uploaded_file():
    assert True


def test_get_data_point():
    assert True


def get_speedup_data():
    assert True


def set_up(ip_addr="localhost", ip_port="8051"):
    # works for linux, no browser pops up
    fireFoxOptions = webdriver.FirefoxOptions()
    fireFoxOptions.add_argument("--headless")
    driver = webdriver.Firefox(options=fireFoxOptions)
    driver.get("http://" + ip_addr + ":" + ip_port + "/")

    return driver


# test order of chart titles
def test_title_order():
    my_parser = create_parser(default_settings)
    parser_args = my_parser.parse_args(
        [
            "-w",
            workload_dir,
        ]
    )

    t = multiprocessing.Process(target=causal, args=(parser_args,))
    t.start()
    time.sleep(10)

    driver = set_up()
    main_page = page.MainPage(driver)

    expected_title_set = [
        "Selected Causal Profiles",
        "cpu_slow_func(long, int)",
        "/home/jose/omnitrace/examples/causal/causal.cpp:165",
        "cpu_fast_func(long, int)",
    ]
    captured_output = main_page.get_titles()
    t.terminate()
    t.join()
    driver.quit()

    assert captured_output == expected_title_set


def test_alphabetical_title_order():
    my_parser = create_parser(default_settings)
    parser_args = my_parser.parse_args(
        [
            "-w",
            workload_dir,
        ]
    )

    t = multiprocessing.Process(target=causal, args=(parser_args,))
    t.start()
    time.sleep(10)
    driver = set_up()
    main_page = page.MainPage(driver)

    expected_title_set = [
        "Selected Causal Profiles",
        "/home/jose/omnitrace/examples/causal/causal.cpp:165",
        "cpu_fast_func(long, int)",
        "cpu_slow_func(long, int)",
    ]

    # expected_histogram_x = ['/home/jose/omnitrace/examples/causal/causal.cpp:153', '/home/jose/omnitrace/examples/causal/causal.cpp:155']
    # expected_histogram_y = [3036, 14983] 

    title_set = main_page.get_alphabetical_titles()
    # captured_histogram = main_page.get_histogram_data()
    captured_plot_data = main_page.get_plot_data()
    
    # captured_histogram_x = captured_histogram["x"][0:2]
    # captured_histogram_y = captured_histogram["y"][-2:]

    t.terminate()
    t.join()
    driver.quit()

    # assert captured_histogram_x == expected_histogram_x
    # assert captured_histogram_y ==expected_histogram_y

    assert((np.array(captured_plot_data[0]["error_y"]["array"]).round(4) == [0.9115, 0.9072, 0.9204, 0.3939]).all())
    assert(captured_plot_data[0]["x"]== [0, 10, 20, 30])
    assert((np.array(captured_plot_data[0]["y"]).round(4)== [ 0.,10.3991 ,18.533  ,19.1749]).all())
    assert((np.array(captured_plot_data[2]["error_y"]["array"]).round(4)== [0.0264, 0.3931, 1.271 , 1.1804]).all())
    assert(captured_plot_data[2]["x"]== [0, 10, 20, 30])
    assert((np.array(captured_plot_data[2]["y"]).round(4)== [ 0.,-1.7623 ,-1.5829 ,-1.6489]).all())

    assert title_set == expected_title_set


def test_max_speedup_title_order():
    my_parser = create_parser(default_settings)
    parser_args = my_parser.parse_args(
        [
            "-w",
            workload_dir,
        ]
    )

    t = multiprocessing.Process(target=causal, args=(parser_args,))
    t.start()
    time.sleep(10)
    driver = set_up()

    main_page = page.MainPage(driver)
    captured_output = main_page.get_max_speedup_titles()
    captured_histogram_data = main_page.get_histogram_data()
    captured_plot_data = main_page.get_plot_data()
    expected_title_set = ['Selected Causal Profiles', '/home/jose/omnitrace/examples/causal/causal.cpp:165', 'cpu_fast_func(long, int)', 'cpu_slow_func(long, int)']

    t.terminate()
    t.join()
    driver.quit()

    assert((np.array(captured_plot_data[0]["error_y"]["array"]).round(4) == [0.9115, 0.9072, 0.9204, 0.3939]).all())
    assert(captured_plot_data[0]["x"]== [0, 10, 20, 30])
    assert((np.array(captured_plot_data[0]["y"]).round(4)== [ 0.,10.3991 ,18.533  ,19.1749]).all())
    assert((np.array(captured_plot_data[2]["error_y"]["array"]).round(4)== [0.0264, 0.3931, 1.271 , 1.1804]).all())
    assert(captured_plot_data[2]["x"]== [0, 10, 20, 30])
    assert((np.array(captured_plot_data[2]["y"]).round(4)== [ 0.,-1.7623 ,-1.5829 ,-1.6489]).all())

    assert captured_output == expected_title_set


def test_min_speedup_title_order():
    my_parser = create_parser(default_settings)
    parser_args = my_parser.parse_args(
        [
            "-w",
            workload_dir,
        ]
    )

    t = multiprocessing.Process(target=causal, args=(parser_args,))
    t.start()
    time.sleep(10)
    driver = set_up()

    main_page = page.MainPage(driver)

    expected_title_set = ['Selected Causal Profiles', '/home/jose/omnitrace/examples/causal/causal.cpp:165', 'cpu_fast_func(long, int)', 'cpu_slow_func(long, int)']
    captured_output = main_page.get_min_speedup_titles()
    captured_histogram_data = main_page.get_histogram_data()
    captured_plot_data = main_page.get_plot_data()

    t.terminate()
    t.join()
    driver.quit()

    assert((np.array(captured_plot_data[0]["error_y"]["array"]).round(4) == [0.9115, 0.9072, 0.9204, 0.3939]).all())
    assert(captured_plot_data[0]["x"]== [0, 10, 20, 30])
    assert((np.array(captured_plot_data[0]["y"]).round(4)== [ 0.,10.3991 ,18.533  ,19.1749]).all())
    assert((np.array(captured_plot_data[2]["error_y"]["array"]).round(4)== [0.0264, 0.3931, 1.271 , 1.1804]).all())
    assert(captured_plot_data[2]["x"]== [0, 10, 20, 30])
    assert((np.array(captured_plot_data[2]["y"]).round(4)== [ 0.,-1.7623 ,-1.5829 ,-1.6489]).all())

    assert captured_output == expected_title_set


def test_impact_title_order():
    my_parser = create_parser(default_settings)
    parser_args = my_parser.parse_args(
        [
            "-w",
            workload_dir,
        ]
    )

    t = multiprocessing.Process(target=causal, args=(parser_args,))
    t.start()

    time.sleep(10)
    driver = set_up()

    main_page = page.MainPage(driver)

    expected_title_set = ['Selected Causal Profiles', 'cpu_slow_func(long, int)', '/home/jose/omnitrace/examples/causal/causal.cpp:165', 'cpu_fast_func(long, int)']
    captured_output = main_page.get_impact_titles()
    captured_histogram_data = main_page.get_histogram_data()
    captured_plot_data = main_page.get_plot_data()

    t.terminate()
    t.join()
    driver.quit()

    assert((np.array(captured_plot_data[0]["error_y"]["array"]).round(4) == [0.9115, 0.9072, 0.9204, 0.3939]).all())
    assert(captured_plot_data[0]["x"]== [0, 10, 20, 30])
    assert((np.array(captured_plot_data[0]["y"]).round(4)== [ 0.,10.3991 ,18.533  ,19.1749]).all())
    assert((np.array(captured_plot_data[2]["error_y"]["array"]).round(4)== [0.0264, 0.3931, 1.271 , 1.1804]).all())
    assert(captured_plot_data[2]["x"]== [0, 10, 20, 30])
    assert((np.array(captured_plot_data[2]["y"]).round(4)== [ 0.,-1.7623 ,-1.5829 ,-1.6489]).all())

    assert captured_output == expected_title_set


def test_min_points_slider():
    my_parser = create_parser(default_settings)
    parser_args = my_parser.parse_args(
        [
            "-w",
            workload_dir,
        ]
    )

    t = multiprocessing.Process(target=causal, args=(parser_args,))
    t.start()
    time.sleep(10)

    driver = set_up()
    main_page = page.MainPage(driver)
    expected_title_set = []
    captured_output = main_page.get_min_points_titles()
    captured_histogram_data = main_page.get_histogram_data()
    captured_plot_data = main_page.get_plot_data()

    t.terminate()
    t.join()
    driver.quit()

    assert captured_output == expected_title_set


def test_verbose_gui_flag_1():
    t = subprocess.Popen(
        [sys.executable, "-m", "source", "-w", workload_dir, "--verbose", "1", "-n", "0"],
        stdout=subprocess.PIPE,
    )

    time.sleep(10)
    driver = set_up()
    main_page = page.MainPage(driver)

    expected_title_set = [
        "Selected Causal Profiles",
        "cpu_slow_func(long, int)",
        "/home/jose/omnitrace/examples/causal/causal.cpp:165",
        "cpu_fast_func(long, int)",
    ]
    captured_title_set = main_page.get_titles()
    t.terminate()
    driver.quit()
    captured_output = t.communicate(timeout=15)[0].decode("utf-8")

    assert captured_title_set == expected_title_set
    assert captured_output


def test_verbose_gui_flag_2():
    t = subprocess.Popen(
        [sys.executable, "-m", "source", "-w", workload_dir, "--verbose", "2", "-n", "0"],
        stdout=subprocess.PIPE,
    )

    expected_title_set = [
        "Selected Causal Profiles",
        "cpu_slow_func(long, int)",
        "/home/jose/omnitrace/examples/causal/causal.cpp:165",
        "cpu_fast_func(long, int)",
    ]
    time.sleep(10)
    driver = set_up()
    main_page = page.MainPage(driver)
    captured_title_set = main_page.get_titles()
    t.terminate()
    driver.quit()
    captured_output = t.communicate(timeout=15)[0].decode("utf-8")

    assert captured_output
    assert captured_title_set == expected_title_set


def test_verbose_gui_flag_3():
    expected_title_set = [
        "Selected Causal Profiles",
        "cpu_slow_func(long, int)",
        "/home/jose/omnitrace/examples/causal/causal.cpp:165",
        "cpu_fast_func(long, int)",
    ]

    t = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "source",
            "-w",
            workload_dir,
            "--verbose",
            "3",
            "-n",
            "0",
        ],
        stdout=subprocess.PIPE,
    )

    time.sleep(10)
    driver = set_up()
    main_page = page.MainPage(driver)

    captured_title_set = main_page.get_titles()
    t.terminate()
    driver.quit()
    captured_output = t.communicate(timeout=15)[0].decode("utf-8")

    assert captured_title_set == expected_title_set
    assert captured_output


def test_ip_port_flag():
    t = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "source",
            "-w",
            workload_dir,
            "--port",
            "8052",
        ],
        stdout=subprocess.PIPE,
    )

    time.sleep(10)
    driver = set_up(ip_port="8052")
    main_page = page.MainPage(driver)

    expected_title_set = [
        "Selected Causal Profiles",
        "cpu_slow_func(long, int)",
        "/home/jose/omnitrace/examples/causal/causal.cpp:165",
        "cpu_fast_func(long, int)",
    ]
    expected_output = "running on http://0.0.0.0:8052"

    captured_title_set = main_page.get_titles()
    t.terminate()
    captured_output = t.communicate(timeout=15)[0].decode("utf-8")

    assert captured_title_set == expected_title_set
    assert expected_output in captured_output

    return True
    t = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "source",
            "-w",
            workload_dir,
            "-n",
            "0",
            "--cli",
            "-p",
            ".*",
        ],
        stdout=subprocess.PIPE,
    )
    # t = subprocess.run(["omnitrace-causal-plot", "-w","/home/jose/omnitrace/source/python/gui/workloads/omnitrace-tests-output/causal-cpu-omni-fast-func-e2e/causal/","--verbose","2", "-n", "0", "--cli", "-p", ".*"], capture_output=True)
    time.sleep(20)
    driver = set_up()

    ## driver.refresh()
    # time.sleep(20)
    main_page = page.MainPage(driver)

    expected_title_set = [
        "Selected Causal Profiles",
        "cpu_slow_func(long, int)",
        "/home/jose/omnitrace/examples/causal/causal.cpp:165",
        "cpu_fast_func(long, int)",
    ]
    # out, err = self.capfd.readouterr()
    expected_output = ""

    # expected_title_set_run = main_page.get_titles()
    print("\nexpected_title_set: ", expected_title_set)
    driver.close()
    # output = subprocess.check_output( stdin=t.stdout)
    captured_output, err = capfd.readouterr()

    print(captured_output)
    with open("capture_output.txt", "w") as text_file:
        text_file.write(captured_output)
    # assert(expected_title_set_run == expected_title_set)
    assert expected_output in captured_output

    # def test_num_points_flag():
    #     self.assertTrue(True,True)

    # def test_speedups_flag():
    #     self.assertTrue(True,True)

    # def test_std_dev_flag():
    #     self.assertTrue(True,True)

    # def test_validate_flag():
    #     self.assertTrue(True,True)
