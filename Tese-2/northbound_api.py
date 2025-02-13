###############################################################
#    Script to evaluate avg and max thput on northbound api   #
###############################################################


import requests, subprocess, threading
import time, csv


def get_response_time(controller, CONTROLLER_IP, REST_PORT):
    if controller == 'onos':
        url = f'http://{CONTROLLER_IP}:{REST_PORT}/onos/v1/topology'
        headers = {'Accept': 'application/json'}
        start_time = time.time()
        response = requests.get(url, headers=headers, auth=('onos', 'rocks'))
        end_time = time.time()
        response_data = response.json()
        #print(response_data)
        # Extract the topology information from the response
        topology = response_data['devices']
        #links = response_data['links']
        if topology > 0:
            response_time = end_time - start_time
            return response_time
        else:
            return 0
        
    elif controller == 'floodlight':
        url1 = f'http://{CONTROLLER_IP}:{REST_PORT}/wm/core/controller/switches/json'
        #url2 = f'http://{CONTROLLER_IP}:{REST_PORT}/wm/topology/links/json'
        try:
            print('here')
            start_time = time.time()
            response1 = requests.get(url1)
            #response2 = requests.get(url2)
            end_time = time.time()
            print('here1')
            if response1.status_code == 200:
                print('200')
                if len(response1.json()) > 0:
                    response_time = end_time - start_time
                    print('response_time')
                    return response_time
                else:
                    print('0')
                    return 0
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
            print('here')
            start_time = time.time()
            response = requests.get(url, headers=headers, auth=auth)
            end_time = time.time()
            print('here1')
            if response.status_code == 200:
                data = response.json()
                if 'node' in data['nodes']:
                    print(' response_time')
                    response_time = end_time - start_time
                    return response_time
                else:
                    print('0')
                    return 0
            else:
                print(f"Error: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

    elif controller == 'ryu':
        url = f'http://{CONTROLLER_IP}:{REST_PORT}/v1.0/topology/switches'
        try:
            start_time = time.time()
            response = requests.get(url)
            end_time = time.time()
            if response.status_code == 200:
                if len(response.json()) > 0:
                    response_time = end_time - start_time
                    return response_time
                else:
                    return 0
            else:
                print(f"Error: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

def send_request(url, headers, auth, result_list):
    try:
        response = requests.get(url, headers=headers, auth=auth)
        if response.status_code == 200:
            result_list.append(1)
    except requests.exceptions.RequestException:
        pass

def measure_throughput(controller, CONTROLLER_IP, REST_PORT, num_requests, duration):
    headers = {'Accept': 'application/json'}
    url = ''
    auth = ()
    if controller == 'onos':
        url = f'http://{CONTROLLER_IP}:{REST_PORT}/onos/v1/topology'
        auth = ('onos','rocks')
    elif controller == 'floodlight':
        url = f'http://{CONTROLLER_IP}:{REST_PORT}/wm/core/controller/switches/json'
        #auth = ('admin','admin')
    elif controller == 'odl':
        url = f'http://{CONTROLLER_IP}:{REST_PORT}/restconf/operational/opendaylight-inventory:nodes'
        auth = ('admin','admin')
    elif controller == 'ryu':
        url = f'http://{CONTROLLER_IP}:{REST_PORT}/v1.0/topology/switches'


    successful_requests = 0
    result_list = []

    start_time = time.time()

    while time.time() - start_time < duration:
        threads = []
        for _ in range(num_requests):
            t = threading.Thread(target=send_request, args=(url, headers, auth, result_list))
            t.start()
            threads.append(t)

        for thread in threads:
            thread.join()

    successful_requests = len(result_list)

    throughput = successful_requests / duration

    return throughput

def evaluate_max_throughput(controller, CONTROLLER_IP, REST_PORT, max_requests, duration, step):
    #step = increment  # Number of concurrent requests increment per step
    current_requests = step
    max_throughput = 0.0

    while current_requests <= max_requests:
        throughput = measure_throughput(controller, CONTROLLER_IP, REST_PORT, current_requests, duration)
        print(f"Concurrent Requests: {current_requests} | Throughput: {throughput} requests per second")

        if throughput > max_throughput:
            max_throughput = throughput

        current_requests += step

    return max_throughput

def initialize_csv(controller_name, topology, folder, request_time, throughput):

    if request_time:
        with open(f'output/{folder}/{controller_name}_{topology}_northbound_api_latency.csv', 'w') as file:
            writer = csv.writer(file)
            writer.writerow(['num_switches', 'min_value','avg_value', 'max_value', 'mdev_value'])
    if throughput:
         with open(f'output/{folder}/{controller_name}_{topology}_northbound_api_throughput.csv', 'w') as file:
            writer = csv.writer(file)
            writer.writerow(['num_switches', 'max_throughput'])



def calculate_stats(response_times):
    if not response_times:
        return None, None, None, None
    
    min_response_time = min(response_times)
    average_response_time = sum(response_times) / len(response_times)
    max_response_time = max(response_times)
    
    
    # Calculating mdev (mean deviation)
    mdev = sum(abs(time - average_response_time) for time in response_times) / len(response_times)
    
    return min_response_time, average_response_time, max_response_time, mdev

def initialize(folder, topology, controller_name, controller_ip, rest_port, size, query_interval, num_tests, request_time, throughput, max_requests, duration, step):

    total_response_times = []
    '''
    if request_time:
        succ_test = 0
        while succ_test < (num_tests):
            response_time = get_response_time(controller_name, controller_ip, rest_port)
            if response_time > 0:
                #print(response_time)
                succ_test += 1
            time.sleep(query_interval)
            total_response_time += response_time
        average_response_time = total_response_time / num_tests
        with open(f'output/{folder}/{controller_name}_{topology}_northbound_api_latency.csv', 'a') as file:
            writer = csv.writer(file)
            writer.writerow([str(size), str(average_response_time)])
        print(f"Average Response Time: {average_response_time}")
    '''
    if request_time:
        succ_test = 0
        while succ_test < (num_tests):
            response_time = get_response_time(controller_name, controller_ip, rest_port)
            if response_time > 0:
                succ_test += 1
                total_response_times.append(response_time)
            time.sleep(query_interval)
            
        min_response_time, max_response_time, average_response_time, mdev = calculate_stats(total_response_times)
        
        with open(f'output/{folder}/{controller_name}_{topology}_northbound_api_latency.csv', 'a') as file:
            writer = csv.writer(file)
            #writer.writerow([str(size), str(average_response_time)])
            writer.writerow([str(size), str(min_response_time), str(average_response_time), str(max_response_time), str(mdev)])
        print(f"Average Response Time: {average_response_time}")
       
    if throughput:
        print('throughput')
        max_throughput = evaluate_max_throughput(controller_name, controller_ip, rest_port, max_requests, duration, step)
        print(f"Max Throughput: {max_throughput} requests per second")
        with open(f'output/{folder}/{controller_name}_{topology}_northbound_api_throughput.csv', 'a') as file:
            writer = csv.writer(file)
            writer.writerow([str(size) , str(max_throughput)])
    return average_response_time, max_throughput
