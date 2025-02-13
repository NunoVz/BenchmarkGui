from scapy.all import IP, ICMP, UDP, send
import random
import sys

def malformed_packets_generator(controller_name, controller_ip, total_packets, valid_percentage, fault_group):
    fault_group = fault_group.split(',')
    if controller_name == 'onos':
        target_ip = '172.17.0.2'
        target_port = '9876'
    elif controller_name == 'odl' or controller_name == 'ryu':
        target_ip = '127.0.0.1'
        target_port = '6653'
    else:
        print("Unknown controller name")
        return

    print('Malformed packets')
    result_log = ""
    def create_normal_packet(ip):
        return IP(dst=ip) / ICMP()

    def create_malformed_packet(ip, payload=b'Malformed', multiplier=1):
        return IP(dst=ip) / ICMP() / (payload * multiplier)

    for _ in range(total_packets):
        if random.random() < valid_percentage / 100:
            packet = create_normal_packet(target_ip)
            print('Sending normal packages')
        else:
            fault_type = random.choice(fault_group)
            if fault_type == 'MP1':
                packet = create_malformed_packet(target_ip)
                print('[MP1] sending malformed packages')
            elif fault_type == 'MP2':
                packet = create_malformed_packet(target_ip, b'Malformed', 2000)
                print('[MP2] sending malformed packages')
            elif fault_type == 'MP3':
                packet = IP(dst=target_ip) / UDP(dport=int(target_port)) / ICMP()  # Changed TCP to UDP
                print('[MP3] sending malformed packages')
            elif fault_type == 'MP4':
                source = '192.168.0.' + str(random.randint(1, 254))
                packet = IP(src=source, dst=target_ip) / ICMP()
                print('[MP4] sending malformed packages')
            else:
                print("Fault Type does not exist")
                break
        result = send(packet, verbose=False)
        result_log += f"Packet sent: {packet.summary()}, Result: {result}\n"
    with open("output.txt", "w") as file:
        file.write(result_log)

if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("Usage: python ines/send.py <controller_name> <controller_ip> <total_packets> <valid_percentage> <fault_group>")
        sys.exit(1)

    controller_name = sys.argv[1]
    controller_ip = sys.argv[2]
    total_packets = int(sys.argv[3])
    valid_percentage = int(sys.argv[4])
    fault_group = sys.argv[5]

    malformed_packets_generator(controller_name, controller_ip, total_packets, valid_percentage, fault_group)