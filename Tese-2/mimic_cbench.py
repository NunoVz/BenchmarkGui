from scapy.all import *
from scapy.contrib.openflow3 import OFPTPacketIn, OFPTPacketOut, OpenFlow3
from scapy.contrib.lldp import LLDPDU
import csv
from mininet.node import Host
import subprocess
import multiprocessing
import concurrent.futures
import time
import os
from arguments_parser import parser

#estes vao ser de auxilio
rtt_file_aux = "output/mimic_cbench_rtt.csv"
throughput_file_aux = "output/mimic_cbench_throughput.csv"


syn_timestamps = {}
packet_in_count = 0
packet_out_count = 0
start_time = time.time()

# Create empty RTT and throughput files
with open(rtt_file_aux, mode='w', newline='') as rtt_csv:
    pass

with open(throughput_file_aux, mode='w', newline='') as throughput_csv:
    pass

def initialize_csv(controller_name, approach, topology, folder, request_time, throughput):
    if throughput or request_time:
        file_prefix = 'pppt' if approach == 'P' else 'rppt'

        filenames = []

        if throughput:
            throughput_filename = f'output/{folder}/{controller_name}_{topology}_{file_prefix}_throughput.csv'
            filenames.append((throughput_filename, ['num_switches', 'throughput']))

        if request_time:
            rtt_filename = f'output/{folder}/{controller_name}_{topology}_{file_prefix}_rtt.csv'
            filenames.append((rtt_filename, ['num_switches', 'min_value','avg_value','max_value','mdev_value']))

        for filename, header_row in filenames:
            print(f"Creating {filename}")
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, 'w') as file:
                writer = csv.writer(file)
                writer.writerow(header_row)

        return filenames

    else:
        print('Select throughput or request_time in initialize_variables.py')
        return None

def calculate(file_path):
    with open(file_path, mode='r') as file:
        reader = csv.reader(file)
        values = [float(row[0]) for row in reader]
        
    if len(values) == 0:
        return None, None, None, None
    
    minimum = min(values)
    average = sum(values) / len(values)
    maximum = max(values)
    mdev = sum(abs(x - average) for x in values) / len(values)
    
    '''
    try:
        os.remove(file_path)
        print(f"Removed {file_path}")
    except Exception as e:
        print(f"Error removing {file_path}: {e}")
    '''
    
    return minimum, average, maximum, mdev

def results(size, controller_name, topology, approach, folder, request_time, throughput):
    time.sleep(30)
    rtt_min, rtt_average, rtt_maximum, rtt_mdev = calculate(rtt_file_aux)
    throughput_min, throughput_average, throughput_maximum, throughput_mdev = calculate(throughput_file_aux)

    print("(", rtt_average, ",", throughput_average, ")")

    file_prefix = 'pppt' if approach == 'P' else 'rppt'

    if throughput:
        filename = f'output/{folder}/{controller_name}_{topology}_{file_prefix}_throughput.csv'
        #print(f"Appending to {filename}")
        with open(filename, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([str(size), str(throughput_average)])
    if request_time:
        filename = f'output/{folder}/{controller_name}_{topology}_{file_prefix}_rtt.csv'
        #print(f"Appending to {filename}")
        with open(filename, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([str(size), str(rtt_min),str(rtt_average), str(rtt_maximum), str(rtt_mdev)])

def packet_callback(pkt):
    global syn_timestamps, packet_in_count, packet_out_count, start_time

    timestamp = pkt.time
    src_port = pkt[TCP].sport
    dst_port = pkt[TCP].dport

    if 'OFPTPacketIn' in pkt.summary():
        if pkt.haslayer(scapy.layers.l2.ARP):  # Detect ARP packets
            packet_in_count += 1
            syn_timestamps[(pkt[IP].src, src_port, pkt[IP].dst, dst_port)] = timestamp

    if 'OFPTPacketOut' in pkt.summary():
        key = (pkt[IP].dst, dst_port, pkt[IP].src, src_port)
        if key in syn_timestamps:
            packet_out_count += 1
            # Calculate RTT
            syn_timestamp = syn_timestamps[key]
            rtt = timestamp - syn_timestamp
            # Remove the SYN timestamp from the dictionary
            del syn_timestamps[key]
            # Write RTT to CSV file
            with open(rtt_file_aux, mode='a') as rtt_csv:
                #print(f"Writing to {rtt_file_aux}")
                rtt_writer = csv.writer(rtt_csv)
                rtt_writer.writerow([rtt])

    current_time = time.time()
    time_elapsed = current_time - start_time
    if time_elapsed > 1:  # Calculate throughput every 1 second
        throughput = (packet_in_count + packet_out_count) / time_elapsed
        if throughput > 0:
            with open(throughput_file_aux, mode='a') as throughput_csv:
                #print(f"Writing to {throughput_file_aux}")
                throughput_writer = csv.writer(throughput_csv)
                throughput_writer.writerow([throughput])
        # Reset counters
        packet_in_count = 0
        packet_out_count = 0
        start_time = current_time

if __name__ == '__main__':
    args = parser('mimic_cbench')

    sniff(prn=packet_callback, filter=f"tcp and port {args.controller_port}", store=0, iface=args.iface)
