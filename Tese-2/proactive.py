import requests
from mininet.node import Host
import subprocess
import concurrent.futures
import time
import json

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
                    #print(f"Host {link.intf1.node.name} ({link.intf1.node.MAC()}) connected to port {intf.name} of switch {switch.name}")
                elif isinstance(link.intf2.node, Host):
                    connected_hosts.append(link.intf2.node)
                    #print(f"Host {link.intf2.node.name} ({link.intf2.node.MAC()}) connected to port {intf.name} of switch {switch.name}")
        if len(connected_hosts) >= 2:
            for i in range(len(connected_hosts)):
                for j in range(i+1, len(connected_hosts)):
                    matched_hosts.append(((connected_hosts[i], connected_hosts[j]), switch))
    return matched_hosts

def create_flow_payload_onos(source_mac, destination_mac, switch_id, in_port, out_port):

    return {
        "flows": [
            {
                "priority": 100,
                "timeout": 0,
                "isPermanent": True,
                "deviceId": "of:"+switch_id.dpid,
                "treatment": {
                    "instructions": [
                        {
                            "type": "OUTPUT",
                            "port": out_port
                        }
                    ]
                },
                "selector": {
                    "criteria": [
                        {
                            "type": "ETH_SRC",
                            "mac": source_mac.MAC()
                        },
                        {
                            "type": "ETH_DST",
                            "mac": destination_mac.MAC()
                        },
                        {
                            "type": "IN_PORT",
                            "port": in_port
                        }
                    ]
                }
            },
            {
                "priority": 100,
                "timeout": 0,
                "isPermanent": True,
                "deviceId": "of:"+switch_id.dpid,
                "treatment": {
                    "instructions": [
                        {
                            "type": "OUTPUT",
                            "port": in_port
                        }
                    ]
                },
                "selector": {
                    "criteria": [
                        {
                            "type": "ETH_SRC",
                            "mac": destination_mac.MAC()
                        },
                        {
                            "type": "ETH_DST",
                            "mac": source_mac.MAC()
                        },
                        {
                            "type": "IN_PORT",
                            "port": out_port
                        }
                    ]
                }
            }
        ]
    }


def generate_flow_payload_odl(flow_id, source_host, destination_host):
    flow_name = f"Flow-{source_host}-{destination_host}"
    xml_payload = f"""
        <?xml version="1.0" encoding="UTF-8" standalone="no"?>
        <flow xmlns="urn:opendaylight:flow:inventory">
            <strict>false</strict>
            <instructions>
                <instruction>
                    <order>1</order>
                    <apply-actions>
                        <action>
                            <order>1</order>
                            <output-action>
                                <output-node-connector>2</output-node-connector>
                            </output-action>
                        </action>
                    </apply-actions>
                </instruction>
            </instructions>
            <table_id>2</table_id>
            <id>{flow_id}</id>
            <cookie_mask>10</cookie_mask>
            <out_port>2</out_port>
            <installHw>false</installHw>
            <match>
                <ethernet-match>
                    <ethernet-type>
                        <type>2048</type>
                    </ethernet-type>
                </ethernet-match>
                <ipv4-source>{source_host.IP()}/24</ipv4-source>
                <ipv4-destination>{destination_host.IP()}/24</ipv4-destination>
            </match>
            <hard-timeout>0</hard-timeout>
            <cookie>10</cookie>
            <idle-timeout>0</idle-timeout>
            <flow-name>{flow_name}</flow-name>
            <priority>2</priority>
            <barrier>false</barrier>
        </flow>
    """
    return xml_payload





def rules_installation(net, controller_name, controller_ip, rest_port, mode):
    matched_hosts = match_hosts(net)
    #matched_hosts = matched_hosts[1:] #ignora o 1º par

    if controller_name == 'onos': #WORKING
        for (source_host, destination_host), switch in matched_hosts:
            in_port = "1"
            out_port = "2"
            time.sleep(10)
            # Fluxo de source_host para destination_host
            flow = create_flow_payload_onos(source_host, destination_host, switch, in_port, out_port)
            print(flow)
            curl_command = f"curl -u onos:rocks -X POST -H 'Content-Type: application/json' -d '{json.dumps(flow)}' http://{controller_ip}:{rest_port}/onos/v1/flows"
            try:
                output = subprocess.check_output(curl_command, shell=True)
                output_decoded = output.decode('utf-8')
                print(output_decoded)
                #if '"code":400' in output_decoded:
                #    print("Error installing flows :", output_decoded)
                #else:
                #    print("Flows installed:", output_decoded)
                #time.sleep(5)
                #verify_flows = f"sudo ovs-ofctl dump-flows {switch} -O OpenFlow13"
                #output  = subprocess.check_output(verify_flows, shell=True)
                #output_decoded = output.decode('utf-8')
                #if '"code":400' in output_decoded:
                #    print("Error verifying flows:", output_decoded)
                #else:
                #    print("Flows:", output_decoded)

            except subprocess.CalledProcessError as e:
                print("Error executing curl:", e)





    elif controller_name == 'odl': # not working
        flow = None
        flow_id = 1
        flow_payload = {
            "opendaylight:flow:inventory" : []
        }
        for (source_host, destination_host), switch in matched_hosts:
            flow_payload = generate_flow_payload_odl(flow_id, source_host, destination_host)
            flow_id += 1
            url = f"http://{controller_ip}:{rest_port}/restconf/config/opendaylight-inventory:nodes/node/{switch}/table/2"
            headers = {'Content-Type': 'application/xml'}
            auth = ('admin', 'admin')
            response = requests.post(url, data=flow_payload, headers=headers, auth=auth)
            if response.status_code == 200:
                print("Flows installed.")
            else:
                print("Error installing flows:", response.text)

    elif controller_name == 'ryu':
        print('Rest Interface does not allow the rules installation')
        response.status_code = 400


    time.sleep(10)





def ping_pair(pair):
    host1, host2 = pair[0]
    print(f"Pinging from {host2.name} ({host2.IP()}) ({host2.MAC()}) to {host1.name} ({host1.IP()}) ({host1.MAC()})")

    try:
        output = host2.cmd(f'ping -i 0.5 -w 60 {host1.IP()}')
        #print('output: ',output)
        
    except subprocess.TimeoutExpired:
        print("Ping timeout expired while pinging", host2.IP())
    except Exception as e:
        print("Error executing ping:", e)


def initialize_ping(net):
    matched_hosts = match_hosts(net)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(ping_pair, matched_hosts)
    print('ping done')
    time.sleep(10)
    
