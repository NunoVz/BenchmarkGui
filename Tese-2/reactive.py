from scapy.contrib.openflow3 import OFPTPacketIn, OFPTPacketOut, OpenFlow3
from scapy.contrib.lldp import LLDPDU
import csv
from mininet.node import Host
import subprocess
import multiprocessing
import concurrent.futures

def match_hosts(net):
    matched_hosts = []
    switches = net.switches
    for switch in switches:
        connected_hosts = []
        for intf in switch.intfList():
            link = intf.link
            if link:
                if isinstance(link.intf1.node, Host):
                    connected_hosts.append(link.intf1.node)
                elif isinstance(link.intf2.node, Host):
                    connected_hosts.append(link.intf2.node)
        if len(connected_hosts) >= 2:
            for i in range(len(connected_hosts)):
                for j in range(i+1, len(connected_hosts)):
                    matched_hosts.append((connected_hosts[i], connected_hosts[j]))
    return matched_hosts

def arping(pair):
    host1, host2 = pair

    try:
        command = host1.cmd(f'arping -W 0.005 -w 60 {host2.IP()}')
        #print(command)
    except Exception as e:
        print("Error executing arping:", e)


def initialize_arping(net):
    matched_hosts = match_hosts(net)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(arping, matched_hosts)
    print('arping done')














