import requests
import time
from arguments_parser import parser
from global_variables import *
from scapy.all import *
from scapy.contrib.openflow3 import OFPTPacketIn, OFPTPacketOut, OpenFlow3
from scapy.contrib.lldp import LLDPDU
from setup_dhcp import setup
from mininet.cli import CLI
from mininet.util import pmonitor





def get_target_link():
    with open('output/link_length.txt','r') as f:
        lines = f.readlines()
        value = int(lines[-1].strip())
    return value

def is_ofpt_packet_out(packet):
    global start_time, total_packets, total_lldp, count_packets, count_lldp
    total_packets += len(packet)
    count_packets += 1
    if 'OFPTPacketOut' in packet.summary():
        start_time = time.time()
        controller_monitor.start() #starts cpu/mem monitoring
        if(packet.getlayer(LLDPDU)):
            total_lldp += len(packet)
            count_lldp +=1
        return True
    else:
        return False

def last_ofpt_packet_in(packet):
    global last_time_pkt_in, total_packets, total_lldp, count_packets, count_lldp
    total_packets += len(packet)
    count_packets += 1
    if topology_match or fail:
        controller_monitor.stop() #stop cpu/mem monitoring
        return True
    else:
        if 'OFPTPacketIn' in packet.summary():
            last_time_pkt_in = time.time()
            if(packet.getlayer(LLDPDU)):
                total_lldp += len(packet)
                count_lldp +=1
        return False


def get_link_size(controller,CONTROLLER_IP, REST_PORT):
    if controller == 'onos':
        url = f'http://{CONTROLLER_IP}:{REST_PORT}/onos/v1/topology'
        headers = {'Accept': 'application/json'}
        response = requests.get(url, headers=headers,auth=('onos','rocks'))
        response_data = response.json()
        links = response_data['links']
        return links
    elif controller == 'floodlight':
        url2 = f'http://{CONTROLLER_IP}:{REST_PORT}/wm/topology/links/json'
        try:
            response2 = requests.get(url2)
            if response2.status_code == 200:
                links = response2.json()
                return len(links)*2
            else:
                print(f"Error: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
    elif controller == 'odl':
        url = f'http://{CONTROLLER_IP}:{REST_PORT}/restconf/operational/opendaylight-inventory:nodes'
        headers = {
            'Accept': 'application/json',
        }
        auth = ('admin', 'admin')
        try:
            response = requests.get(url, headers=headers, auth=auth)
            if response.status_code == 200:
                data = response.json()
                if 'node' in data['nodes']:
                    nodes = data['nodes']['node']
                    link_count = 0
                    host_count = 0
                    for node in nodes:
                        node_connectors = node.get('node-connector', [])
                        for connector in node_connectors:
                            state = connector.get('flow-node-inventory:state', {})
                            link_down = state.get('link-down', False)
                            if not link_down:
                                link_count += 1
                        if node_connectors and node.get('node-type') == 'OF':
                            host_count += 1
                    return link_count #odl adds one local link for each sw
                else:
                    return 0
            else:
                print(f"Error: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

def get_host_size(controller,CONTROLLER_IP, REST_PORT):
    if controller == 'onos':
        url2 = f'http://{CONTROLLER_IP}:{REST_PORT}/onos/v1/hosts'
        headers = {'Accept': 'application/json'}
        response2 = requests.get(url2, headers=headers,auth=('onos','rocks'))
        host_Data = response2.json()
        hosts = len(host_Data['hosts'])
        hosts_with_ip = sum(1 for h in host_Data['hosts'] if len(h['ipAddresses']) == 1)
        #print(hosts_with_ip)
        return hosts
    elif controller == 'floodlight':
        url3 = f'http://{CONTROLLER_IP}:{REST_PORT}/wm/device/'
        try:
            response3 = requests.get(url3)
            if response3.status_code == 200:
                hosts = response3.json()
                host_count = sum(1 for h in hosts['devices'] if len(h['attachmentPoint']) == 1)
                return host_count
            else:
                print(f"Error: {response3.status_code} - {response3.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
    elif controller == 'odl':
        url = f"http://{CONTROLLER_IP}:{REST_PORT}/restconf/operational/network-topology:network-topology"
        headers = {
            'Accept': 'application/json',
        }
        auth = ('admin', 'admin')
        try:
            response = requests.get(url, headers=headers, auth=auth)
            if response.status_code == 200:
                data = response.json()
                host_count = 0
                if "network-topology" in data and "topology" in data["network-topology"]:
                    for topology in data["network-topology"]["topology"]:
                        if topology["topology-id"] == "flow:1":  # Adjust topology-id based on your setup
                            nodes = topology.get("node", [])
                            for node in nodes:
                                if "node-id" in node and node["node-id"].startswith("host:"):
                                    host_count += 1
                # Step 4: Count the number of host devices
                print (host_count)
                return host_count
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")


def on_off_link(links_to_add, additional_links, controller_name, controller_ip, rest_port):
    sum_times_on, sum_times_off = 0,0
    for i in range(0,10):
        start_time = time.time()
        num_links_to_bring_up = links_to_add  # Adjust this number as per your requirement
        existent_links = get_target_link()
        intf2_links = random.sample(additional_links, num_links_to_bring_up)
        for link in intf2_links:
            subprocess.run(['ifconfig', link, 'up'])
            
        while get_link_size(controller_name,controller_ip, rest_port) != existent_links+(num_links_to_bring_up*2):
            continue
        end_time = time.time()
        sum_times_on += (end_time - start_time)
    
        print(f'link on time_{i} = {end_time - start_time}')

        start_time = time.time()
        for link in intf2_links:
            subprocess.run(['ifconfig', link, 'down'])
        while get_link_size(controller_name,controller_ip, rest_port) != existent_links:
            continue
        end_time = time.time()
        sum_times_off += (end_time - start_time)
        print(f'link off time_{i} = {end_time - start_time}')
        time.sleep(random.randint(1,10))
    print(f'link on avg time = {sum_times_on/10}')
    print(f'link off  avgtime = {sum_times_off/10}')
    #CLI(net)

def on_off_hosts(hosts_switches, hosts_to_on, net, controller_name, controller_ip, rest_port):
    sum_times_on, sum_times_off = 0,0
    for i in range(0,10):
        if i > 0:
            for j in range(hosts_to_on):
                tuple = hosts_switches[j]
                switch = net.switches[tuple[0]-1]
                switch.attach(f's{tuple[0]}-eth{tuple[1]}')

        
        CLI(net)
        for j in range(hosts_to_on):
            host = net.hosts[j]
            next_host = net.hosts[(j + 1) % hosts_to_on]
            host.cmd(f'ping -c 1 {next_host.IP()} &')
            
        start_time = time.time() #CHANGE IT TO START WHEN DETECT THE FIRST PACKET_IN MESSAGE ARIVING AT CONTROLLER
        while get_host_size(controller_name,controller_ip, rest_port) != hosts_to_on:
            time.sleep(1)

        end_time = time.time()
        sum_times_on += (end_time - start_time)
        print(f'host on time_{i} = {end_time - start_time}')
        CLI(net)
        start_time = time.time()
        for j in range(hosts_to_on):
            tuple = hosts_switches[j]
            switch = net.switches[tuple[0]-1]
            switch.detach(f's{tuple[0]}-eth{tuple[1]}')

        while get_host_size(controller_name,controller_ip, rest_port) != 0:
            time.sleep(1)
            continue
        end_time = time.time()
        sum_times_off += (end_time - start_time)
        print(f'host off time_{i} = {end_time - start_time}')
    print(f'link on avg time = {sum_times_on/10}')
    print(f'link off  avgtime = {sum_times_off/10}')

def on_off_hosts_dhcp(hosts_to_add, net, controller_name, controller_ip, rest_port):
    sum_times_on, sum_times_off = 0,0
    for i in range(0,10):
        additional_hosts = []
        num_hosts_to_add = hosts_to_add  # Number of additional hosts to add
        switches_to_attach = list(range(1, len(net.switches)+1))  # List of switches to attach the hosts to
        attached_hosts = []  # List to store the attached host tuples (switch, port)
        tuples = []
        for j in range(num_hosts_to_add):
            switch_index = random.choice(switches_to_attach)  # Choose a random switch to attach the host
            switch = net.switches[switch_index - 1]
            host = net.addHost(f'h{j}')
            additional_hosts.append(host)
            switch_port = len(switch.ports)  # Find the next available port on the switch
            link = net.addLink(host, switch, port1=0, port2=switch_port)
            interface_name = link.intf1.name  # Get the name of the host's interface connected to the switch
            switch.attach(f's{switch_index}-eth{switch_port}')
            attached_hosts.append((switch_index, switch_port))  # Store the switch and port tuple    
            tuples.append([switch_index,switch_port]) # this is only for floodlight
            
        
        setup(controller_name,controller_ip,rest_port,tuples)
        time.sleep(1)
        start_time = time.time()
        for host in additional_hosts:
            host.cmd('dhclient &')
        
        while get_host_size(controller_name,controller_ip, rest_port) != num_hosts_to_add:
            #for host in additional_hosts:
            #    host.cmd('dhclient &')
            time.sleep(1)
        end_time = time.time()
        sum_times_on += (end_time - start_time)
        print(f'host on time_{i} = {end_time - start_time}')
        time.sleep(1)
        start_time = time.time()
        for switch_index, switch_port in attached_hosts:
            switch = net.switches[switch_index - 1]
            switch.detach(f's{switch_index}-eth{switch_port}')
        while get_host_size(controller_name,controller_ip, rest_port) != 0:
            time.sleep(1)
            continue
        end_time = time.time()
        sum_times_off += (end_time - start_time)
        print(f'host off time_{i} = {end_time - start_time}')
        for host in additional_hosts:
            net.delHost(host)
        time.sleep(1)
    print(f'link on avg time = {sum_times_on/10}')
    print(f'link off  avgtime = {sum_times_off/10}')
    #CLI(net)    

def compare_topology(topology, len_topology):
    # Check if the topology matches the deployed topology
    if topology == len_topology:
        return True
    else:
        return False

def calculate_topology_discovery_time(start_time, end_time):
    topology_discovery_time = end_time - start_time
    return topology_discovery_time