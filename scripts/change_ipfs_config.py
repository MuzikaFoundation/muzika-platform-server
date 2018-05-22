
import os
import json
import argparse

args = argparse.ArgumentParser()
args.add_argument('--path', help='config file path')
args = args.parse_args()

# Loads configuration for IPFS
ipfs_config_file = args.path or os.path.join(os.path.expanduser('~'), '.ipfs', "config")
with open(ipfs_config_file) as f:
    config = json.loads(f.read())

# Change configuration for IPFS
config['Swarm']['DisableRelay'] = False
config['Swarm']['EnableRelayHop'] = True

websocket_address = "/ip4/0.0.0.0/tcp/4004/ws"
if websocket_address not in config['Addresses']['Swarm']:
    config['Addresses']['Swarm'].append(websocket_address)

# Save the changed config file
with open(ipfs_config_file, 'w') as f:
    f.write(json.dumps(config))
