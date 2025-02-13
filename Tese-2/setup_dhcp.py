import requests, json

def setup(controller,CONTROLLER_IP, REST_PORT, tuples):
    if controller == 'onos':
        url = f'http://{CONTROLLER_IP}:{REST_PORT}/onos/v1/network/configuration/'
        headers = {
            'Content-Type': 'application/json',
        }
        config = open('json/onos_dhcp.json').read()
        response = requests.post(url, data=config, headers=headers,auth=('onos','rocks'))
        if response.status_code == 200:
                return response
        else:
            print(f"Error: {response.status_code} - {response.text}")
    elif controller == 'floodlight':
        json_data = {
           "switchports": []
        }
        for tuple in tuples:
            #switch_dpid = switch.dpid[15:]  # Extract the switch number from the dpid (e.g., s7 -> 7)
            #for port, switch_port in switch.ports.items():
            link_entry = {
                "dpid": str(tuple[0]),
                "port": str(tuple[1])
            }
            json_data['switchports'].append(link_entry)
        json_str = json.dumps(json_data, indent=4)
        with open('json/tuples.json', "w") as file:
            file.write(json_str)
        headers = {
            'Content-Type': 'application/json',
            'Accept-Type': 'application/json'
        }
        config = open('json/enable.json').read()
        instance = open('json/instance1.json').read()
        tuples = open('json/tuples.json').read()
        vlans = open('json/vlans.json').read()

        instance_name = 'dhcp-server'
        config_url = f'http://{CONTROLLER_IP}:{REST_PORT}/wm/dhcp/config'
        instance_url = f'http://{CONTROLLER_IP}:{REST_PORT}/wm/dhcp/instance'
        vlan_url = f'http://{CONTROLLER_IP}:{REST_PORT}/wm/dhcp/instance/{instance_name}'
        tuple_url = f'http://{CONTROLLER_IP}:{REST_PORT}/wm/dhcp/instance/{instance_name}'
        try:
            response1 = requests.post(config_url,data=config,headers=headers)
            response2 = requests.post(instance_url,data=instance,headers=headers)
            response3 = requests.post(vlan_url,data=vlans,headers=headers)
            response4 = requests.post(tuple_url,data=tuples,headers=headers)
            if response1.status_code == 200:
                resp = response1.json()
                return resp
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
