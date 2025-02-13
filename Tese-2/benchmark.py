
# imports
from arguments_parser import parser
import subprocess
import workload
import southbound_NN_api
import northbound_api
import mimic_cbench
import proactive
import reactive
import attackload
import time
import multiprocessing
from multiprocessing.shared_memory import SharedMemory
import script_topology
import faultload

import sys
sys.path.append('/home/admin/.local/lib/python3.10/site-packages')
import schedule


def check_and_restart_openvswitch():
    try:
        # Check the status of the openvswitch-switch service
        status_result = subprocess.run(['sudo', 'systemctl', 'status', 'openvswitch-switch'], capture_output=True, text=True)

        # Check if "Dependency failed for Open vSwitch." is in the output
        if "Dependency failed for Open vSwitch." in status_result.stdout:
            print("Dependency failed. Restarting Open vSwitch...")

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

    except Exception as e:
        print(f"An error occurred: {e}")

def get_target(topo, size, type='sep'):
    if topo == 'mesh':
        return size

    elif topo == 'leaf-spine':
        if type == 'sep':
            return size, size*2
        else:
            return (size + size*2)

    elif topo == '3-tier':
        if type == 'sep':
            return int(size/3), int(size/3), int(size/3)
        else:
            return size #(size + size + size)



if __name__ == '__main__':
    args = parser('benchmark')
    #print(sys.path)
    schedule.every(10).seconds.do(check_and_restart_openvswitch)

    print("Current Topology Type:", args.topology)

    # Determine the folder based on the arguments
    if args.denial_of_service:
        folder = 'DoS'
    elif args.slowloris:
        folder = 'slowloris'
    elif args.fault_type == 'Rest':
        folder = 'rest'
        total_packets = None
        valid_percentage = None
        mf_groups = None
        num_faults =  args.num_faults
        value_int =  args.value_int
        value_representation =  args.value_representation
        value_string =  args.value_string
        fault_groups =  args.fault_groups
        maximum = args.maximum
    elif args.fault_type == 'MP':
        folder = 'malformed'
        total_packets = args.total_packets
        valid_percentage = args.valid_percentage
        mf_groups = args.mf_groups
        num_faults = None
        value_int = None
        value_representation = None
        value_string = None
        fault_groups = None
        maximum = None
    else:
        folder = 'traffic'

    ping = True
    if args.metrics == 'TDT':
        script_topology.initialize_csv(args.controller_name, args.topology)
        
    elif args.metrics == 'N':
        ping = False if args.controller_name == 'odl' else True
        northbound_api.initialize_csv(args.controller_name, args.topology, folder, args.request_time, args.throughput)
        
    elif args.metrics == 'NN' or args.metrics == 'NNP':
        ping = False if args.metrics == 'NNP'  else True
        southbound_NN_api.initialize_csv(args.metrics, args.controller_name, args.topology, folder, args.request_time, args.throughput)

    elif args.metrics == 'P' or args.metrics == 'R':
        mimic_cbench.initialize_csv(args.controller_name, args.metrics,args.topology, folder, args.request_time, args.throughput)
        ping = False

    # initial number of switches (s), final number of switches (maxsize), iterating q in q
    for size in range(args.start, args.maxsize + 1, args.query_interval):
        print("Current topology size:", size)

        if args.metrics == 'TDT':
            script_topology.initialize(args.controller_name, args.controller_ip, args.controller_port, args.rest_port, args.topology , size, args.query_interval, args.iface, args.trials, args.consec_failures,  args.nolinks)
          
        else:
            print('Running workload.initialize')
            net, cl = workload.initialize(args.controller_name, args.controller_ip, args.controller_port,  args.rest_port, get_target(args.topology,size,'sep'), args.topology, args.hosts, args.hosts_to_add, args.links, args.links_to_add, ping)

            
            print('Traffic Generator')
            stop_event = multiprocessing.Event()
            traffic_process = multiprocessing.Process(target=workload.generate_traffic, args=(cl, stop_event))
            traffic_process.start()
            
            client = None
            # WORKING
            if args.denial_of_service or args.slowloris:
                print('Attackload Generator')
                client = attackload.connection(args.controller_ip)
                attack_process = multiprocessing.Process(target=attackload.initialize, args=(folder, args.controller_name, args.controller_ip, args.rest_port, client))
                attack_process.start()
            
            if args.fault_type != "None":
                print('Faultload Generator')
                fault_process = multiprocessing.Process(target=faultload.initialize, args=(folder, args.controller_name, args.controller_ip,args.rest_port, total_packets, valid_percentage, mf_groups, num_faults, value_int, value_representation, value_string, fault_groups, maximum))
                fault_process.start()

            if args.metrics == 'P':
                print('Proactive Mode')
                #proactive.rules_delete( args.controller_name,args.controller_ip,args.rest_port)
                #proactive.rules_installation(net, args.controller_name, args.controller_ip, args.rest_port, 'drop') # Drop all ARP packets
                print('Running mimic_cbench.py')
                def run_mimic_cbench():
                    subprocess.run(['python3', 'mimic_cbench.py','-p', str(args.controller_port), '-i', str(args.iface)])
                mimic_process = multiprocessing.Process(target=run_mimic_cbench)
                mimic_process.start()

                print('Installing Flows')
                proactive.rules_installation(net, args.controller_name, args.controller_ip, args.rest_port,'create')
                print('Initializing Ping')
                ping_process = multiprocessing.Process(target= proactive.initialize_ping, args=(net,))
                ping_process.start()
                
                ping_process.join()
                mimic_process.terminate()

                mimic_cbench.results(size, args.controller_name, args.topology, args.metrics, folder, args.request_time, args.throughput)
                #proactive.rules_delete( args.controller_name,args.controller_ip,args.rest_port)

            
            if args.metrics == 'NNP':
                print('Not working yet')
                '''
                print('Node-to-Node Proactive Mode')
                max_distance, max_distance_hosts = southbound_NN_api.find_max_distance_hosts(net)
                print('Installing Flows')
                # Installing Flows with max_distance_hosts information
                southbound_NN_response_time = southbound_NN_api.initialize_NNP(max_distance_hosts, folder, net, args.topology, args.controller_name, size, args.num_tests, args.max_requests, args.duration, args.step, args.request_time, args.throughput)
                print(southbound_NN_response_time)
                '''

            elif args.metrics == 'R':
                print('Reactive Mode')
                print('Running mimic_cbench.py')
                def run_mimic_cbench():
                    subprocess.run(['python3', 'mimic_cbench.py','-p', str(args.controller_port), '-i', str(args.iface)])
                mimic_process = multiprocessing.Process(target=run_mimic_cbench)
                mimic_process.start()
                print('Initializing arping')
                reactive.initialize_arping(net)
                mimic_process.terminate()
                mimic_cbench.results(size, args.controller_name, args.topology, args.metrics, folder, args.request_time, args.throughput)
            
            elif args.metrics == 'N':
                print('Running northbound_api')
                northbound_response_time = northbound_api.initialize(folder, args.topology ,args.controller_name, args.controller_ip, args.rest_port, size, args.query_interval, args.num_tests, args.request_time, args.throughput, args.max_requests, args.duration, args.step)
                print(northbound_response_time)
           
            elif  args.metrics == 'NN':
                print('Running southbound_NN_api')
                southbound_NN_response_time = southbound_NN_api.initialize(folder, net, args.topology, args.controller_name, size, args.num_tests, args.max_requests, args.duration, args.step, args.request_time, args.throughput)
                print(southbound_NN_response_time)
                
            
            if args.denial_of_service or args.slowloris:
                attackload.stop_connection(client)
                attack_process.terminate()
                print('Finished Attackload Generator')
           
            if args.fault_type != "None":
                fault_process.terminate()
                print('Finished Faultload Generator')
            
            stop_event.set()
            traffic_process.join()
            print('Finished traffic generator')
            
            workload.terminate(net)
            print('Finished Network')
    schedule.clear()
    print('Finished Benchmark')
