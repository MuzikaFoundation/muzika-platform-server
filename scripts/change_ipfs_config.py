
import os
import json

# Loads configuration for IPFS
ipfs_config_file = os.path.join(os.getenv("HOME"), ".ipfs", "config")
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
