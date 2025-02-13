
###########################################################################
#    Script to evaluate avg and max thput on southbound api node-to-node  #
###########################################################################


from sys import maxsize
import requests, subprocess, threading
import time
import networkx as nx
import itertools
from collections import defaultdict
import heapq, random
from concurrent.futures import ThreadPoolExecutor
import csv
import re
import math

def initialize_csv(mode, controller_name, topology, folder, request_time, throughput):
    if throughput:
        with open(f'output/{folder}/{controller_name}_{topology}_southbound_{mode}_api_throughput.csv', 'w') as file:
            writer = csv.writer(file)
            writer.writerow(['num_switches', 'max_throughput'])

    if request_time:
        with open(f'output/{folder}/{controller_name}_{topology}_southbound_{mode}_api_latency.csv', 'w') as file:
            writer = csv.writer(file)
            writer.writerow(['num_switches', 'min_time', 'avg_time','max_time', 'mdev', 'avg_time_excl_max'])
            #[str(size) , str(min_time), str(max_time), str(avg_time), str(mdev), str(avg_time_excl_max)])

def dijkstra(graph, start):
    distances = defaultdict(lambda: float('inf'))
    distances[start] = 0
    pq = [(0, start)]

    while pq:
        dist, node = heapq.heappop(pq)

        if dist > distances[node]:
            continue

        for neighbor, weight in graph[node].items():
            if distances[node] + weight < distances[neighbor]:
                distances[neighbor] = distances[node] + weight
                heapq.heappush(pq, (distances[neighbor], neighbor))

    return distances


def calculate_distances(net):
    graph = defaultdict(dict)

    # Conexões entre switches
    for switch in net.switches:
        for intf in switch.intfList():
            link = intf.link
            if link:
                other_switch = link.intf2.node
                graph[switch.name][other_switch.name] = 1
                graph[other_switch.name][switch.name] = 1

    # Conexões entre switches e hosts
    for host in net.hosts:
        for intf in host.intfList():
            link = intf.link
            if link:
                connected_node = link.intf2.node
                graph[host.name][connected_node.name] = 1
                graph[connected_node.name][host.name] = 1

    distances = {}

    # Calcular as distâncias mínimas usando o algoritmo de Dijkstra
    for node_id in graph.keys():
        distances[node_id] = dijkstra(graph, node_id)

    # Remover distâncias que não são entre hosts
    for host_id in list(distances.keys()):
        if not any(host_id == host.name for host in net.hosts):
            del distances[host_id]

    return distances



def find_max_distance_hosts(net): #versão correta

    distances = calculate_distances(net)

    max_distance = 0

    for host, dist in distances.items():
        max_dist_for_host = max(dist.values(), default=-1)
        if max_dist_for_host > max_distance:
            max_distance = max_dist_for_host

    max_distance_pairs = []
    for host, dist in distances.items():
        for neighbor, d in dist.items():
            if d == max_distance:
                max_distance_pairs.append((host, neighbor))

    return max_distance, max_distance_pairs

def find_info(net, max_distance_hosts):
    print('max_distance_hosts',max_distance_hosts)

    host1_name = max_distance_hosts[0][0]
    host2_name = max_distance_hosts[0][1]

    host1_info = None
    host2_info = None

    for host in net.hosts:
        if host.name == host1_name:
            host1_info = host
        elif host.name == host2_name:
            host2_info = host

    if host1_info is None:
        raise ValueError(f"Host {host1_name} not found")
    if host2_info is None:
        raise ValueError(f"Host {host2_name} not found")

    host2_ip = host2_info.IP()

    return host1_info, host2_ip

'''
# USAR ESTA VERSÃO PARA O MODO PROATIVO ONDE É OBRIGATORIO O HOST1 SER IMPAR POIS O PROACTIVO NÃO CONHECE HOSTS PARES!
def find_info(net, max_distance_hosts):
    # Function to check if a host name is odd-numbered
    def is_odd_numbered(host_name):
        match = re.search(r'(\d+)', host_name)
        if match:
            number = int(match.group(1))
            return number % 2 != 0
        return False

    # Initialize host info to None
    host1_info, host2_info = None, None

    # Iterate over the max_distance_hosts list to find a valid odd-numbered host pair
    for host1_name, host2_name in max_distance_hosts:
        if is_odd_numbered(host1_name):
            # Find the host info in the network
            for host in net.hosts:
                if host.name == host1_name:
                    host1_info = host
                elif host.name == host2_name:
                    host2_info = host
            if host1_info and host2_info:
                break

    # Check if a valid pair was found
    if host1_info is None or host2_info is None:
        raise ValueError("No valid host pair with an odd-numbered host found")

    host2_ip = host2_info.IP()

    return host1_info, host2_ip


# USAR PARA O PROACTIVO 
def initialize_NNP(max_distance_hosts, folder, net, topology, controller_name, size, num_tests, max_requests, duration, step, request_time, throughput):
    host1, host2 = find_info(net, max_distance_hosts)

    print(host1, host2)

    if request_time:
        min_time, max_time, avg_time, mdev, avg_time_excl_max = get_response_time(host1, host2, num_tests)
        print(f"Average Response Time: {avg_time_excl_max}")
        with open(f'output/{folder}/{controller_name}_{topology}_southbound_NN_api_latency.csv', 'a') as file:
            writer = csv.writer(file)
            writer.writerow([str(size) , str(min_time), str(avg_time), str(max_time), str(mdev), str(avg_time_excl_max)])
    if throughput: # só vai funcionar quando o de cima funcionar
        max_throughput = evaluate_max_throughput(host1, host2, max_requests, duration, step)
        print(f"Max Throughput: {max_throughput} requests per second")
        with open(f'output/{folder}/{controller_name}_{topology}_southbound_NN_api_throughput.csv', 'a') as file:
            writer = csv.writer(file)
            writer.writerow([str(size) , str(max_throughput)])

    return avg_time_excl_max , max_throughput
'''



def get_response_time(source, destiny_ip, n_tests):
    command = source.cmd(f"ping -c {n_tests} {destiny_ip}")
    output_lines = command.split('\n')
    print('output_lines:', output_lines)
    min_time, max_time, avg_time, mdev, avg_time_excl_max = None, None, None, None, None
    time_pattern = re.compile(r'time=(\d+\.\d+) ms')
    response_times = []

    for line in output_lines:
        if "Destination Host Unreachable" in line:
            print("Destination Host Unreachable")
            return None, None, None, None, None
        elif "100% packet loss" in line:
            print("100% packet loss")
            return None, None, None, None, None
        elif "rtt min/avg" in line:
            print(line)
            avg_time_parts = line.split('=')[1].split('/')
            min_time = float(avg_time_parts[0])
            avg_time = float(avg_time_parts[1])
            max_time = float(avg_time_parts[2])
            mdev = float(avg_time_parts[3].split()[0])
            
            # Calcula a média excluindo o valor máximo
            avg_time_excl_max = (avg_time * n_tests - max_time) / (n_tests - 1)
            
            return min_time, avg_time, max_time, mdev, avg_time_excl_max
        else:
            match = time_pattern.search(line)
            if match:
                response_times.append(float(match.group(1)))

    if response_times:
        min_time = min(response_times)
        max_time = max(response_times)
        avg_time = sum(response_times) / len(response_times)
        avg_time_excl_max = (avg_time * n_tests - max_time) / (n_tests - 1) if len(response_times) > 1 else None
        
        squared_diff_sum = sum((time - avg_time) ** 2 for time in response_times)
        mdev = math.sqrt(squared_diff_sum / len(response_times))
        
        print(f"Minimum Response Time: {min_time} ms")
        print(f"Maximum Response Time: {max_time} ms")
        print(f"Average Response Time: {avg_time} ms")
        print(f"Average Response Time (excluding max): {avg_time_excl_max} ms")
        print(f"Standard Deviation: {mdev} ms")
        
        return min_time, avg_time, max_time, mdev, avg_time_excl_max
    return min_time, avg_time, max_time, mdev, avg_time_excl_max
'''
def get_response_time(source, destiny_ip, n_tests):
    #c = source.cmd(f"ping -c 1 {destiny_ip}")
    command = source.cmd(f"ping -c {n_tests} {destiny_ip}")
    #print(f"ping -c {n_tests} {destiny_ip}")
    output_lines = command.split('\n')
    print('output_lines:', output_lines)
    time_pattern = re.compile(r'time=(\d+\.\d+) ms')
    response_times = []
    avg_time = None
    for line in output_lines:
        if "Destination Host Unreachable" in line:
            print("Destination Host Unreachable")
            return None
        elif "100% packet loss" in line:
            print("100% packet loss")
            return None
        elif "rtt min/avg" in line:
            print(line)
            avg_time_parts = line.split('=')[1].split('/')
            avg_time = float(avg_time_parts[1])
            mdev = float(avg_time_parts[3].split()[0])
            return avg_time, mdev
        else:
            match = time_pattern.search(line)
            if match:
                response_times.append(float(match.group(1)))

    if response_times and avg_time == None:
        print('response_times', response_times)
        avg_time = sum(response_times) / len(response_times)
        print(f"Average Response Time: {avg_time} ms")
        squared_diff_sum = sum((time - avg_time) ** 2 for time in response_times)
        mdev = math.sqrt(squared_diff_sum / len(response_times))
        print(f"Standard Deviation: {mdev} ms")
        return avg_time, mdev
'''
def send_request(source, destiny_ip, n_tests, result_list):
    #c = source.cmd(f"ping -c 1 {destiny_ip}")
    command = source.cmd(f"ping -c {n_tests} {destiny_ip}")
    #print(f"ping -c {n_tests} {destiny_ip}")
    output_lines = command.split('\n')
    #print('output_lines:', output_lines)
    for line in output_lines:
        if "rtt min/avg" in line:
            result_list.append(1)


def measure_throughput(host1, host2, num_requests, duration):
    successful_requests = 0
    result_list = []

    start_time = time.time()
    #end_time = start_time + duration

    while time.time() - start_time < duration:
        threads = []
        for _ in range(num_requests):
            t = threading.Thread(target=send_request, args=(host1, host2, 1,result_list))
            t.start()
            threads.append(t)
            t.join()

    successful_requests = len(result_list)

    throughput = successful_requests / duration

    return throughput


def evaluate_max_throughput(host1, host2, max_requests, duration, step):
    current_requests = step
    max_throughput = 0

    while current_requests <= max_requests:
        throughput = measure_throughput(host1, host2, current_requests, duration)
        print(f"Concurrent Requests: {current_requests} | Throughput: {throughput} requests per second")

        if throughput > max_throughput:
            max_throughput = throughput

        current_requests += step

    return max_throughput




def initialize(folder, net, topology, controller_name, size, num_tests, max_requests, duration, step, request_time, throughput):

    avg_time , max_throughput = None, None
    max_distance, max_distance_hosts = find_max_distance_hosts(net)
    print("max_distance: ", max_distance)

    host1, host2 = find_info(net, max_distance_hosts)

    print(host1, host2)

    if request_time:
        min_time, max_time, avg_time, mdev, avg_time_excl_max = get_response_time(host1, host2, num_tests)
        print(f"Average Response Time: {avg_time_excl_max}")
        with open(f'output/{folder}/{controller_name}_{topology}_southbound_NN_api_latency.csv', 'a') as file:
            writer = csv.writer(file)
            writer.writerow([str(size) , str(min_time), str(avg_time), str(max_time), str(mdev), str(avg_time_excl_max)])
    if throughput: # só vai funcionar quando o de cima funcionar
        max_throughput = evaluate_max_throughput(host1, host2, max_requests, duration, step)
        print(f"Max Throughput: {max_throughput} requests per second")
        with open(f'output/{folder}/{controller_name}_{topology}_southbound_NN_api_throughput.csv', 'a') as file:
            writer = csv.writer(file)
            writer.writerow([str(size) , str(max_throughput)])

    return avg_time_excl_max , max_throughput
