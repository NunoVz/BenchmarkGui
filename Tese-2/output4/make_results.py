import os
import csv

# Lista de pastas
folders = ['traffic', 'DoS', 'slowloris', 'rest', 'malformed']

# Dicionários para armazenar os resultados
results_avg_time_excl_max = {}
results_max_time = {}
results_avg_time = {}
results_mdev = {}

# Iterando sobre as pastas
for folder in folders:
    filepath = os.path.join('.', folder, 'onos_mesh_southbound_NN_api_latency.csv')
    if os.path.exists(filepath):
        with open(filepath, 'r') as file:
            csv_reader = csv.reader(file)
            header = next(csv_reader)
            # Corrige o cabeçalho se estiver incorreto
            if header[0] != 'num_switches' or header[1] != 'min_time' or header[2] != 'avg_time' or header[3] != 'max_time' or header[4] != 'mdev' or header[5] != 'avg_time_excl_max':
                header = ['num_switches', 'min_time', 'avg_time', 'max_time', 'mdev', 'avg_time_excl_max']
            for row in csv_reader:
                switchers = int(row[0])
                avg_time_excl_max = row[5]
                max_time = row[3]
                avg_time = row[2]
                mdev = row[4]
                if switchers not in results_avg_time_excl_max:
                    results_avg_time_excl_max[switchers] = {}
                    results_max_time[switchers] = {}
                    results_avg_time[switchers] = {}
                    results_mdev[switchers] = {}
                results_avg_time_excl_max[switchers][folder] = avg_time_excl_max
                results_max_time[switchers][folder] = max_time
                results_avg_time[switchers][folder] = avg_time
                results_mdev[switchers][folder] = mdev

# Função para escrever resultados em um arquivo CSV
def write_results_to_csv(filename, results, fieldnames, folder_mapping):
    if not os.path.exists('Results'):
        os.makedirs('Results')
    filepath = os.path.join('Results', filename)
    with open(filepath, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for switchers, data in results.items():
            row = {'Switchers': switchers}
            for folder, fieldname in folder_mapping.items():
                row[fieldname] = data.get(folder, '')
            writer.writerow(row)

# Nomes de campo para os arquivos CSV
fieldnames = ['Switchers', 'Traffic', 'DoS', 'Slowloris', 'RestFaults', 'MalformedPackets']
folder_mapping = {
    'traffic': 'Traffic',
    'DoS': 'DoS',
    'slowloris': 'Slowloris',
    'rest': 'RestFaults',
    'malformed': 'MalformedPackets'
}

# Escrevendo os resultados em arquivos CSV
write_results_to_csv('onos_mesh_southbound_NN_api_latency_avg_time_excl_max.csv', results_avg_time_excl_max, fieldnames, folder_mapping)
print("Arquivo CSV de avg_time_excl_max gerado com sucesso:", os.path.join('Results', 'onos_mesh_southbound_NN_api_latency_avg_time_excl_max.csv'))

write_results_to_csv('onos_mesh_southbound_NN_api_latency_max_time.csv', results_max_time, fieldnames, folder_mapping)
print("Arquivo CSV de max_time gerado com sucesso:", os.path.join('Results', 'onos_mesh_southbound_NN_api_latency_max_time.csv'))

write_results_to_csv('onos_mesh_southbound_NN_api_latency_avg_time.csv', results_avg_time, fieldnames, folder_mapping)
print("Arquivo CSV de avg_time gerado com sucesso:", os.path.join('Results', 'onos_mesh_southbound_NN_api_latency_avg_time.csv'))

write_results_to_csv('onos_mesh_southbound_NN_api_latency_mdev.csv', results_mdev, fieldnames, folder_mapping)
print("Arquivo CSV de mdev gerado com sucesso:", os.path.join('Results', 'onos_mesh_southbound_NN_api_latency_mdev.csv'))
