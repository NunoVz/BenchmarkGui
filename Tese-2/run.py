import subprocess
import argparse
import time
import paramiko, requests, os

def connection(controller_ip):
    try:
        print("Connecting to the controller...")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(controller_ip, username="admin", key_filename="/home/admin/.ssh/id_rsa")
        print("Connected to the controller.")
        return client
    except paramiko.AuthenticationException:
        print("Authentication failed. Please check your credentials.")
    except paramiko.SSHException as ssh_err:
        print(f"SSH error: {ssh_err}")
    except Exception as e:
        print(f"Error: {e}")
    return None

def execute_docker_commands(controller, client, metrics):
    def run_command(command):
        stdin, stdout, stderr = client.exec_command(command)
        stdout_output = stdout.read().decode()
        stderr_output = stderr.read().decode()
        return stdout_output, stderr_output

    if controller == 'onos':
        print("Stopping ONOS container...")
        stop_output, stop_error = run_command("docker stop onos")
        print(f"{stop_output} {stop_error}")

        print("Removing ONOS container...")
        rm_output, rm_error = run_command("docker rm onos")
        print(f"{rm_output} {rm_error}")

        print("Running ONOS container...")

        if metrics == 'P': # Desativar o reactive forwarding
            run_output, run_error = run_command(
                "docker run -d -p 8181:8181 -p 8101:8101 -p 5005:5005 -p 830:830 -p 6633:6633 -p 6653:6653 -e ONOS_APPS=drivers,openflow,proxyarp,gui2 --name onos onosproject/onos"
            )
        else:
            run_output, run_error = run_command(
                "docker run -d -p 8181:8181 -p 8101:8101 -p 5005:5005 -p 830:830 -p 6633:6633 -p 6653:6653 -e ONOS_APPS=drivers,openflow,proxyarp,reactive-routing,fwd,gui2 --name onos onosproject/onos"
            )
        print(f"{run_output} {run_error}")

        print("Fetching ONOS logs...")
        logs_output, logs_error = run_command("docker logs onos | tail")
        print(f"ONOS logs (tail):\n{logs_output} {logs_error}")

    elif controller == 'odl':
        print("Checking for ODL process...")
        pids_output, _ = run_command("pgrep -f 'karaf'")
        pids = pids_output.strip().split()

        if pids:
            for pid in pids:
                print(f"Killing ODL process with PID: {pid}")
                run_command(f"kill {pid}")

            print("Verifying ODL processes terminated...")
            remaining_pids_output, _ = run_command("pgrep -f 'karaf'")
            if not remaining_pids_output.strip():
                print("All ODL processes have been terminated.")
            else:
                print(f"Failed to terminate the following ODL processes: {remaining_pids_output.strip()}")
        else:
            print("No ODL process found.")

        time.sleep(10)
        print("Changing to ODL directory and starting ODL...")
        odl_output, odl_error = run_command(f"cd ~/odl/karaf-0.8.4 && ./bin/karaf")
        print(f'ODL started; {odl_output} {odl_error}')

    elif controller == 'ryu':
        print("Checking for Ryu processes...")
        pids_output, _ = run_command("pgrep -f 'ryu-manager'")
        pids = pids_output.strip().split()

        if pids:
            for pid in pids:
                print(f"Killing Ryu process with PID: {pid}")
                run_command(f"kill {pid}")

            print("Verifying Ryu processes terminated...")
            remaining_pids_output, _ = run_command("pgrep -f 'ryu-manager'")
            if not remaining_pids_output.strip():
                print("All Ryu processes have been terminated.")
            else:
                print(f"Failed to terminate the following Ryu processes: {remaining_pids_output.strip()}")
        else:
            print("No Ryu process found.")

        print("Activating Ryu environment and starting Ryu manager...")
        ryu_output, ryu_error = run_command("source ~/ryu/bin/activate && ryu-manager --observe-links ryu.app.simple_switch_stp_13 ryu.app.rest_topology")
        print(f'RYU started; {ryu_output} {ryu_error}')


def stop_connection(client):
    try:
        print("Closing connection...")
        client.close()
        print("Closed")
    except Exception as e:
        print(f"Error while closing connection: {e}")


def check_and_restart_openvswitch():
    try:
        # Start the openvswitch-switch service
        start_result = subprocess.run(['sudo', 'systemctl', 'start', 'openvswitch-switch'], capture_output=True, text=True)
        if start_result.returncode == 0:
            print("Open vSwitch started successfully.")
        else:
            print(f"Error starting Open vSwitch: {start_result.stderr}")
        # Enable the openvswitch-switch service to start on boot
        enable_result = subprocess.run(['sudo', 'systemctl', 'enable', 'openvswitch-switch'], capture_output=True, text=True)
        if enable_result.returncode == 0:
            print("Open vSwitch enabled to start on boot successfully.")
        else:
            print(f"Error enabling Open vSwitch: {enable_result.stderr}")
        # Check the status of the openvswitch-switch service
        status_result = subprocess.run(['sudo', 'systemctl', 'status', 'openvswitch-switch'], capture_output=True, text=True)
        # Check if "Dependency failed for Open vSwitch." is in the output
        if "Dependency failed for Open vSwitch." in status_result.stdout:
            check_and_restart_openvswitch()
        else:
            print("Open vSwitch is running correctly.")

    except Exception as e:
        print(f"An error occurred: {e}")

def verify_connection(controller, CONTROLLER_IP, REST_PORT):
    headers = {'Accept': 'application/json'}

    if controller == 'onos':
        url = f'http://{CONTROLLER_IP}:{REST_PORT}/onos/v1/hosts'
        auth = ('onos', 'rocks')
    elif controller == 'odl':
        url = f'http://{CONTROLLER_IP}:{REST_PORT}/restconf/operational/opendaylight-inventory:nodes'
        auth = ('admin', 'admin')
    elif controller == 'ryu':
        url = f'http://{CONTROLLER_IP}:{REST_PORT}/v1.0/topology/switches'
        auth = None
    else:
        print("Unsupported controller")
        return False

    try:
        response = requests.get(url, headers=headers, auth=auth)
        response.raise_for_status()
        print("Connection successful!")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Connection failed: {e}")
        return False


def run_benchmark(controller_name, topology, metrics, ip_addr, port, rest, op=None, fault_type=None):

    client = connection(ip_addr)
    if client:
        execute_docker_commands(controller_name,client, metrics)
        time.sleep(10)
        connected = False
        while connected == False:
            connected = verify_connection(controller_name, ip_addr, rest)
            time.sleep(10)
        stop_connection(client)
        time.sleep(10)

    check_and_restart_openvswitch()

    max_value = '30' if topology == '3-tier' else '27'
    cmd = ['sudo', 'python3', 'benchmark.py', '-ip', ip_addr, '-p', port, '-s', '12', '-q', '3', '-max', max_value, '-n', controller_name, '-t', topology, '-m', metrics]

    if op:
        cmd.append(op)
    if fault_type:
        cmd.extend(['-fault', fault_type])
    if rest == '8080': #ryu
        cmd.extend(['-rest_port', rest])

    print(cmd)
    subprocess.run(cmd)



if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='SDN Benchmarking')
    parser.add_argument('-cn', '--controller_name', choices=['onos', 'ryu', 'odl'], required=True, help='Controller name')
    args = parser.parse_args()

    ip = "193.137.203.34"
    p = '6653'
    r = '8080' if args.controller_name == 'ryu' else '8181'

    #for controller_name in ['onos', 'ryu', 'odl']: # Se os controllers estivessem funcionais

    #for topology in ['3-tier', 'mesh']:
    #    for metrics in ['P', 'R', 'N', 'NN']: #  'TDT'
    for metrics in ['P']:
        for topology in ['mesh']: #for topology in ['3-tier', 'mesh']:
            #run_benchmark(args.controller_name, topology, metrics, ip, p, r)
            if metrics != 'TDT':
                #for op in ['-slow']: #for op in ['-dos', '-slow']:
                #    run_benchmark(args.controller_name, topology, metrics, ip, p, r, op)
                for fault_type in ['MP', 'Rest']:
                    run_benchmark(args.controller_name, topology, metrics, ip, p, r, fault_type=fault_type)
