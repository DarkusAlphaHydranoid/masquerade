# Copyright 2024 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import signal
import subprocess
import time
import unittest

import launch
import launch.actions
import launch.substitutions
import launch_ros.actions
import launch_testing.actions
import launch_testing.markers
import pytest


proc_env = os.environ.copy()
proc_env['RMW_IMPLEMENTATION'] = 'rmw_zenoh_cpp'

@pytest.mark.launch_test
@launch_testing.markers.keep_alive
def generate_test_description():

    workspace_directory = launch.substitutions.LaunchConfiguration('workspace_directory')
    workspace_directory_arg = launch.actions.DeclareLaunchArgument('workspace_directory')

    zenoh_router = launch_ros.actions.Node(
        package="rmw_zenoh_cpp",
        executable="rmw_zenohd",
        output="both",
        env=proc_env
    )

    dut_process = launch.actions.ExecuteProcess(
        # colcon test --packages-select demo_nodes_cpp --install-base /opt/ros/rolling --test-result-base . --base-paths /opt/ros/rolling/
        cmd=[
            '/ros_entrypoint.sh',
            'colcon',
            'test',
            '--packages-select',
            'test_rclcpp',
            '--retest-until-pass',
            '2',
            '--merge-install',
            '--base-paths',
            os.path.join('/opt/ros/', 'jazzy'),
            '--install-base', 
            os.path.join('/opt/ros/', 'jazzy')
        ],
        shell=True,
        env=proc_env,
        cwd=workspace_directory
    )

    return launch.LaunchDescription([
        workspace_directory_arg,
        zenoh_router,
        dut_process,
        # In tests where all of the procs under tests terminate themselves, it's necessary
        # to add a dummy process not under test to keep the launch alive. launch_test
        # provides a simple launch action that does this:
        launch_testing.util.KeepAliveProc(),
        launch_testing.actions.ReadyToTest()
    ]) , {'dut_process': dut_process}

class TestTerminatingProcessStops(unittest.TestCase):
    def test_proc_terminates(self, proc_info, dut_process):
        proc_info.assertWaitForShutdown(process=dut_process, timeout=400000)

# These tests are run after the processes in generate_test_description() have shutdown.
@launch_testing.post_shutdown_test()
class TestShutdown(unittest.TestCase):

    def test_exit_codes(self, proc_info):
        """Check if the processes exited normally."""
        launch_testing.asserts.assertExitCodes(proc_info)
