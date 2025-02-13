import csv, time, argparse
import subprocess
import os
import workload


def run_topology_discovery(controller_ip , controller_port, controller_name, rest_port, target_length, query_interval, iface, consec_failures, nolinks):
    if nolinks:
        cmd = ['python3', 'topology_discovery.py', '-ip', controller_ip, '-p', controller_port, '-n', controller_name, '-r', str(rest_port),'-l', str(target_length),'-q', str(query_interval),'-c', str(consec_failures),'-if', iface, '-k']
    else:
        cmd = ['python3', 'topology_discovery.py', '-ip', controller_ip, '-p', controller_port, '-n', controller_name, '-r', str(rest_port),'-l', str(target_length),'-q', str(query_interval),'-c', str(consec_failures),'-if', iface]
    print(cmd)
    return subprocess.Popen(cmd,stdout=subprocess.PIPE)


def write_to_csv(filename, data):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['num_nodes', 'avg_tdt', 'avg_ldt', 'avg_total','avg_lldp_len','avg_pkt_len','avg_lldp_count','avg_pkt_count','avg_cpu','avg_memory\n'])
        writer.writerows(data)


def initialize_csv(controller_name, topology):
    with open('output/traffic/' + controller_name + '_' + topology + '_average_topology_discovery_time.csv', 'w') as file:
        file.write('num_nodes; avg_tdt; avg_ldt; avg_total; avg_lldp_len; avg_pkt_len; avg_lldp_count; avg_pkt_count; avg_cpu; avg_memory\n')

def report(filename, args, run_data):
    report = ''
    for arg in vars(args):
        if getattr(args,arg) != None:
            report += (f'{arg}: {getattr(args, arg)}\n')
    for lines in run_data:
        report += str(lines)+'\n'
    with open(filename, 'w', newline='') as f:
        f.write(report)

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


def initialize(controller_name, controller_ip, controller_port, rest_port, topology, size, query_interval, iface, trials, consec_failures,  nolinks):
    
    avg_file = 'output/traffic' + controller_name + '_' + topology + '_average_topology_discovery_time.csv'
    report_file = 'output/traffic' + controller_name + '_' + topology + '_topology_discovery_time_report.txt'

    data = []
    running_data = []
    running = True
    #i = args.start

    ldt_sum, tdt_sum, lldp_sum, lldp_sum_count, pkt_sum, pkt_sum_count, count_cpu, count_mem = 0, 0, 0, 0, 0, 0, 0, 0

    target_length = size
    disc_stats, link_stats, pkt_stats = [], [], []


    for j in range(0, trials):
        print('running topology.py')
        topology_proc = run_topology_discovery(controller_ip, controller_port, controller_name, rest_port, get_target(topology,size,'agg'),  query_interval, iface, consec_failures, nolinks)
        # time.sleep(1)
        print('running workload.py')
        net, cl = workload.initialize(controller_name, controller_ip, controller_port,  rest_port, get_target(topology,size,'sep'), topology, 0, 'False', False)
        print('done')

        # Wait for topology.py to finish execution
        topology_proc.wait()  # Wait for topology.py to finish
        print('finished topology.py')

        workload.terminate(net)


        # Read the last line of the output file generated by topology.py
        with open('output/topo_disc_' + controller_name + '.txt', 'r') as f:
            lines = f.readlines()
            last_line = lines[-1].strip()
            values = last_line.split(",")

            if len(values) > 1:
                if len(values) == 8:
                    topology_discovery_time, total_discovery_time, total_lldp, count_lldp, total_pkt, count_pkt, avg_cpu, avg_memory = float(
                        values[0]), float(values[1]), float(values[2]), float(values[3]), float(values[4]), float(
                        values[5]), float(values[6]), float(values[7])
                else:
                    print('problem')
                    topology_discovery_time = -1.0
                 #   topology_discovery_time, total_discovery_time = float(
                  #      values[0]), float(values[1])
                link_discovery_time = total_discovery_time - topology_discovery_time
            else:
                topology_discovery_time = -1.0

            if topology_discovery_time != -1.0:
                disc_stats.append(topology_discovery_time)
                pkt_stats.append([total_lldp, count_lldp, total_pkt, count_pkt])
                link_stats.append(link_discovery_time)
                print(disc_stats)
                tdt_sum += total_discovery_time
                ldt_sum += link_discovery_time
                lldp_sum += total_lldp
                lldp_sum_count += count_lldp
                pkt_sum += total_pkt
                pkt_sum_count += count_pkt
                count_cpu += avg_cpu
                count_mem += avg_memory
            else:
                running = False
                break

        # Append the topology discovery time to the topology_output.txt file
        # with open('topology_output.txt', 'a') as f:
        #    f.write(f"{topology_discovery_time}\n")

    avg_tdt, avg_ldt, avg_lldp, avg_lldp_count, avg_pkt, avg_pkt_count, avg_cpu_final, avg_mem = (
        tdt_sum / trials), (ldt_sum / trials), (lldp_sum / trials), (lldp_sum_count / trials), (
                                           pkt_sum / trials), (pkt_sum_count / trials), (
                                           count_cpu / trials), (count_mem / trials)
    data.append(
        [target_length, avg_tdt, avg_ldt, (avg_tdt + avg_ldt), avg_lldp, avg_pkt, avg_lldp_count, avg_pkt_count,
         avg_cpu_final, avg_mem])
    running_data.append([target_length, disc_stats, link_stats, pkt_stats])
    print(data)

    #write_to_csv(avg_file, data)
    with open('output/traffic/' + controller_name + '_' + topology + '_average_topology_discovery_time.csv', 'a') as file:
        file.write(str(data) + '\n')
