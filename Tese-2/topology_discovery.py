import requests
import time
from arguments_parser import parser
from global_variables import *
from scapy.all import *
from scapy.contrib.openflow3 import OFPTPacketIn, OFPTPacketOut, OpenFlow3
from scapy.contrib.lldp import LLDPDU





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
        #controller_monitor.start() #starts cpu/mem monitoring
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
    if (topology_match or fail) and last_time_pkt_in != None:
        #controller_monitor.stop() #stop cpu/mem monitoring
        return True
    else:
        if 'OFPTPacketIn' in packet.summary():
            last_time_pkt_in = time.time()
            print(last_time_pkt_in)
            if(packet.getlayer(LLDPDU)):
                total_lldp += len(packet)
                count_lldp +=1
        return False


def get_topology(controller,CONTROLLER_IP, REST_PORT):
    if controller == 'onos':
        url = f'http://{CONTROLLER_IP}:{REST_PORT}/onos/v1/topology'
        headers = {'Accept': 'application/json'}
        response = requests.get(url, headers=headers,auth=('onos','rocks'))
        response_data = response.json()
        #print(response_data)
        # Extract the topology information from the response
        topology = response_data['devices']
        links = response_data['links']
        return topology, links
    elif controller == 'floodlight':
        url1 = f'http://{CONTROLLER_IP}:{REST_PORT}/wm/core/controller/switches/json'
        url2 = f'http://{CONTROLLER_IP}:{REST_PORT}/wm/topology/links/json'
        try:
            response1 = requests.get(url1)
            response2 = requests.get(url2)
            if response1.status_code == 200:
                switches = response1.json()
                links = response2.json()
                return len(switches), len(links)*2
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
            response = requests.get(url,headers=headers,auth=auth)
            if response.status_code == 200:
                data = response.json()
                if 'node' in data['nodes']:
                    nodes = data['nodes']['node']
                    links = sum(len(node.get('node-connector', [])) for node in nodes)
                    return len(nodes), (links-len(nodes))#odl adds one local link for each sw
                else:
                    return 0
            else:
                print(f"Error: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

    elif controller == 'ryu':
        url_switches = f'http://{CONTROLLER_IP}:{REST_PORT}/v1.0/topology/switches'
        url_links = f'http://{CONTROLLER_IP}:{REST_PORT}/v1.0/topology/links'

        switches = []
        links = []

        try:
            # Retrieve switches information
            response_switches = requests.get(url_switches)
            response_links = requests.get(url_links)

            # Check if the requests were successful (status code 200)
            if all(response.status_code == 200 for response in [response_switches, response_links]):
                switches = response_switches.json()
                links = response_links.json()

                # Extract unique switch IDs (dpid)
                switch_ids = set(entry['dpid'] for entry in switches)
                links_ids = set(entry['dpid'] for entry in links)

                return len(switch_ids), len(links_ids)

            else:
                # Print an error message if any of the requests fail
                for response in [response_switches, response_links]:
                    print(f"Error: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

def compare_topology(topology, len_topology):
    # Check if the topology matches the deployed topology
    if topology == len_topology:
        return True
    else:
        return False

def calculate_topology_discovery_time(start_time, end_time):
    topology_discovery_time = end_time - start_time
    return topology_discovery_time


def start_pkt_in_sniff():
    global pkt_in_sniff
    pkt_in_sniff = sniff(iface=args.iface, filter=f'tcp and dst port {args.controller_port}', stop_filter=last_ofpt_packet_in)


def stop_pkt_in_sniff():
    global pkt_in_sniff
    if pkt_in_sniff:
        pkt_in_sniff.join(timeout=2)  # Wait for the sniffing thread to finish gracefully


def RFC8456_net_topology_discovery_time(len_topology,controller,ctrl_ip, rest_port):
    global topology_match, fail, target_links, end_time, total_packets, count_lldp
    QUERY_INTERVAL = args.query_interval
    pkt_in_sniff_thread = threading.Thread(target=start_pkt_in_sniff)  # Initialize pkt_in_sniff_thread here

    print("Waiting for the first OFPTPacketOut message...")
    sniff(iface=f'{args.iface}',filter=f'tcp and src port {args.controller_port}',stop_filter=is_ofpt_packet_out)
    
    pkt_in_sniff_thread.start()


    #print(' Start sniffing Packet-In messages after the first sniff ends')
    # Query the controller every t=3 seconds to obtain the discovered network topology information
    consecutive_failures, consec_link_failures = 0,0
    while True:
        topology, links = get_topology(controller,ctrl_ip, rest_port)
        print(topology,links)
        if compare_topology(topology, len_topology):
            if end_time == None:
                # Record the time for the last discovery message sent to the controller
                end_time = last_time_pkt_in
                print(end_time)
            if args.no_links:
                topology_match = True
                pkt_in_sniff_thread.join()
                end_time_links = 0
                break
            else:
                if target_links == None:
                    target_links = get_target_link()
                if links == (target_links*2):
                    topology_match = True
                    pkt_in_sniff_thread.join()
                    end_time_links = last_time_pkt_in
                    break
                else:
                    consec_link_failures +=1
                    if consec_link_failures >= args.consec_link_failures:
                        topology_match = False
                        with open('output/topo_disc_'+controller+'.txt', 'a') as f:
                            f.write(f"{args.consec_failures * args.query_interval},{args.consec_failures * args.query_interval},{total_lldp},{count_lldp},{total_packets},{count_packets}\n")
                        break
        else:
            consecutive_failures += 1
            if consecutive_failures >= args.consec_failures:
                fail = True
                with open('output/topo_disc_'+controller+'.txt', 'a') as f:
                    f.write(f"{args.consec_failures * args.query_interval},{args.consec_failures * args.query_interval},{total_lldp},{count_lldp},{total_packets},{count_packets}\n")
                break

        time.sleep(QUERY_INTERVAL)

    # Calculate the topology discovery time
    if topology_match:
        # Collect the measurements from each controller monitor
        cpu_usage = [0]#controller_monitor.cpu_usage
        memory_usage = [0]#controller_monitor.memory_usage

        # Calculate average CPU and memory usage for each controller
        avg_cpu = sum(cpu_usage) / len(cpu_usage)
        avg_memory = sum(memory_usage) / len(memory_usage)
        print('CPU: ',cpu_usage)
        print('Memory: ',memory_usage)
        print('Avg_CPU: ',avg_cpu)
        print('Avg_Memory: ',avg_memory)
        print('total packets: ',total_packets)
        topology_discovery_time = calculate_topology_discovery_time(start_time, end_time)
        print('topology_discovery_time: ',topology_discovery_time)
        with open('output/topo_disc_'+controller+'.txt', 'a') as f:
            if args.no_links:
                f.write(f"{topology_discovery_time},{topology_discovery_time},{total_lldp},{count_lldp},{total_packets},{count_packets},{avg_cpu},{avg_memory}\n")
            else:
                f.write(f"{topology_discovery_time},{end_time_links-start_time},{total_lldp},{count_lldp},{total_packets},{count_packets},{avg_cpu},{avg_memory}\n")
    else:
        print('does not match')
        
if __name__ == '__main__':

    # Parse the command line arguments
    args = parser('topology')
    print(args)
    with open('output/topo_disc_'+args.controller_name+'.txt', 'w') as f:
        pass

    RFC8456_net_topology_discovery_time(args.target_length,
                                        args.controller_name,
                                        args.controller_ip,
                                        args.rest_port)
