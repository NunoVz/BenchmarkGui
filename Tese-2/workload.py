import subprocess, multiprocessing
import random, time
from mininet.cli import CLI
from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from arguments_parser import parser
from mininet.node import Host
from host_links_onoff import on_off_link, on_off_hosts
import os
import threading
import signal


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
            check_and_restart_openvswitch()
        else:
            print("Open vSwitch is running correctly.")
    except Exception as e:
        print(f"An error occurred: {e}")

def get_hosts_per_switch(net):
    hosts_per_switch = {}
    for switch in net.switches:
        hosts_per_switch[switch.name] = []
        for intf in switch.intfList():
            link = intf.link
            if link:
                if isinstance(link.intf1.node, Host):
                    hosts_per_switch[switch.name].append(link.intf1.node)
                elif isinstance(link.intf2.node, Host):
                    hosts_per_switch[switch.name].append(link.intf2.node)
    return hosts_per_switch


def assign_hosts_to_switches(num_sw, num_clients):
    client_connections = []
    ports_per_switch = {}  # Dictionary to keep track of the next available port for each switch

    for client_id in range(1, num_clients + 1):
        switch_id = random.randint(1, num_sw)

        # If the switch is not in the dictionary yet, add it with port number 1
        if switch_id not in ports_per_switch:
            ports_per_switch[switch_id] = 1

        port = ports_per_switch[switch_id]
        client_connections.append([switch_id, port])

        # Increment the port for the selected switch for the next iteration
        ports_per_switch[switch_id] += 1

    return client_connections

def assign_hosts_per_switch(net, num_hosts, switches):
    hosts = []
    global_host_count = 0
    for switch in switches:
        switch_hosts = []
        for j in range(num_hosts):
            global_host_count += 1
            host_name = 'h{}'.format(global_host_count)
            host = net.addHost(host_name)
            switch_hosts.append(host)
            net.addLink(host, switch)
        hosts.append(switch_hosts)
    return hosts


def circular_ping(net, trigger_interval):
    while True:
        hosts_per_switch = get_hosts_per_switch(net)
        for switch, hosts in hosts_per_switch.items():
            print(switch)
            for i in range(len(hosts)):
                src_host = hosts[i]
                dst_host = hosts[(i + 1) % len(hosts)]
                print(src_host, dst_host)
                src_host.cmd('ping -c 1 {}'.format(dst_host.IP()))
        time.sleep(trigger_interval)


def generate_topology(topology_type, topology_parameters):
    if topology_type == 'star':
        num_switches, hub_switch = topology_parameters
        connections = [[] for _ in range(num_switches)]
        for i in range(1, num_switches+1):
            if i != hub_switch:
                connections[i-1].append(hub_switch)

        return connections, num_switches
    elif topology_type == 'mesh':
        num_switches = topology_parameters #[0]
        return [[j+1 for j in range(num_switches) if j!= i] for i in range(num_switches)], num_switches
    elif topology_type == 'leaf-spine':
        num_leafs, num_spines = topology_parameters
        connections = [[] for _ in range(num_leafs)]
        start = num_leafs
        for i in range(num_leafs):
            for j in range(num_spines):
                connections[i].append(start+j+1)
        return connections, (num_leafs+num_spines)
    elif topology_type == '3-tier':
        num_cores, num_aggs, num_access = topology_parameters
        connections = [[] for i in range(num_cores+num_aggs)]
        # Connect core switches horizontally and to all aggregation switches
        for i in range(num_cores):
            if i+1 < num_cores:
                connections[i].append(i+2)
            for j in range(num_aggs):
                connections[i].append(j+num_cores+1)

        # Connect aggregation switches horizontally and to half of the access switches
        start = num_cores
        for i in range(num_aggs):
            if i+1 < num_aggs:
                connections[start+i].append(start+i+2)
            for j in range(num_access//2):
                if (start+i)-num_cores < num_aggs//2:
                    connections[start+i].append(start+num_aggs+j+1)
                else:
                    connections[start+i].append(start+num_aggs+(num_access//2)+j+1)

        if num_access % 2 == 1:
            connections[start+i].append(num_cores+num_aggs+num_access)
        return connections, (num_cores+num_aggs+num_access)


def traffic(clients):

    def on_finished(result, node):
        print(f"{node.name} finished with exit code {result}")

    dst_host = random.choice(clients)
    src_host = random.choice([client for client in clients if client != dst_host])
    port = random.randint(3000,8000)

    cmd = 'sourcesonoff -v -t -d {} --doff-type=weibull --don-min=10 --don-max=1000 --doff-min=1s --doff-max=2s --random-seed {} --turn 3 >> log_{}.txt'.format(dst_host[0].IP(),  random.randrange(1000), src_host[0].name)
    #print('cmd', cmd)
    src_host[0].cmd('echo {} > log_{}.txt'.format(time.strftime("%H%M%S.%f")[:-3], src_host[0].name))

    src_host[0].sendCmd(cmd, printPid=True, callback=lambda result: on_finished(result, src_host))


def generate_traffic(clients, stop_event):
    traffic_processes = []

    while not stop_event.is_set():
        p = multiprocessing.Process(target=traffic, args=(clients,))
        traffic_processes.append(p)
        p.start()

        time.sleep(1)

    for p in traffic_processes:
        p.terminate()

def generate_network(net, topology, num_switches, links, client_links, server_links, controller_data, hosts_to_add):
    switches = []
    for i in range(num_switches):
        switch = net.addSwitch('s{}'.format(i+1), protocols=['OpenFlow13'])
        switches.append(switch)
    clients = []

    clients = assign_hosts_per_switch(net, hosts_to_add, switches)


    servers = []
    for i in range(len(server_links)):
        host = net.addHost('srv{}'.format(i+1))
        servers.append(host)
        switch_index, port_number = server_links[i]
        switch = switches[switch_index - 1]
        net.addLink(host, switch, port1=0, port2=port_number)
    additional_links = []
    for i, neighbors in enumerate(topology):
        switch = switches[i]
        for neighbor in neighbors:
            if neighbor <= num_switches:
                neighbor_switch = switches[neighbor - 1]
                net.addLink(switch, neighbor_switch)
                if links:
                    link = net.addLink(neighbor_switch, switch)
                    #print(link)
                    #link.intf2.config(up=False)  # Set the second interface of the link to down
                    interface_name = link.intf2.name  # Get the name of the second interface
                    additional_links.append(interface_name)
                    subprocess.run(['ifconfig', interface_name, 'down'])  # Set the interface to a down state


    c0 = net.addController('c0', controller=RemoteController, ip=controller_data[0], port=int(controller_data[1]))

    return clients, servers, switches, additional_links



def terminate(net):
    check_and_restart_openvswitch()
    try:
        print('Attempting to stop the network...')
        net.stop()
        print('Network stopped. Attempting to clean up Mininet...')
        process = subprocess.run(['mn', '-c'], check=True)
        if process.returncode == 0:
            print('Cleanup successful')
        else:
            print('Cleanup failed with return code:', process.returncode)
    except subprocess.CalledProcessError as e:
        print('An error occurred while cleaning up Mininet:', e)
    except Exception as e:
        print('An unexpected error occurred:', e)
    finally:
        print('Terminate function execution completed.')


def initialize(controller_name, controller_ip, controller_port, rest_port, topology_parameters, topology_type, hosts, hosts_to_add, links, links_to_add, ping):

    #input_param, args = parser('workload')
    #print(input_param)
    net = Mininet(controller=RemoteController, switch=OVSSwitch)

    print('generate_topology')
    topology, num_sw = generate_topology(topology_type, topology_parameters)


    print('assign_hosts_to_switches')
    client_links = assign_hosts_to_switches( num_sw, hosts_to_add)
    server_links = [] #[[2,3],[1,4]] # o problema está aqui!!! como é vazio nunca vai entrar no for e por consequencia vai dar sempre out of range !

    print('generate_network')
    cl, srv, sw, additional_links = generate_network(net, topology, num_sw, links, client_links, server_links,[controller_ip, controller_port], hosts_to_add)


    print('net starting')
    net.start()
    print('here')
    if controller_name == 'ryu': # Spanning Tree Protocol
        for switch in sw:
            subprocess.run(['ovs-vsctl', 'set', 'Bridge', switch.name, 'protocols=OpenFlow13'])
    print('here1')
    with open('output/link_length.txt','w') as f:
        f.write(f'{len(net.links)-(len(client_links)+len(server_links))}')
    #print(links, hosts)
    #if not links and not hosts:
     #   CLI(net)


    if links:
        on_off_link(links_to_add, additional_links, controller_name, controller_ip, rest_port)

    '''
    if hosts:
        #on_off_hosts(client_links, args.hosts_to_add, net, args.controller_name, args.controller_ip, args.rest_port)
        #circular_ping(net, 30)
    num_hosts = num_sw * hosts_to_add
    for j in range(num_hosts):
        host = net.hosts[j]
        next_host = net.hosts[(j + 1) % num_hosts]
        host.cmd(f'ping -c 1 {next_host.IP()} &')
    '''
    
    if ping == True:
        time.sleep(10)
        net.pingAll()

    print('workload done')


    return net, cl
