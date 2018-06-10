
# Muzika Backend

Muzika backend supports artists to upload paper files, spread out the files to IPFS network and to create contracts
for registering the artists' paper in the block chain network.

### Install IPFS
Install IPFS from https://ipfs.io/docs/install

### Modify IPFS Configuration
After installing IPFS, execute IPFS daemon and it will create a new config file `~/.ipfs/config`.

```
$ ipfs daemon
```

Change IPFS config file(saved in `~/.ipfs/config`) to support websocket for interacting with IPFS nodes in
client browser.

```
$ vi ~/.ipfs/config
{
  ...
  "Addresses": {
    "Swarm": [
      ...
      "/ip4/0.0.0.0/tcp/4004/ws",
    ]
  }
  ...
  "Swarm": {
    ...
    "DisableRelay": false,
    "EnableRelayHop": true,
  }
  ...
}
```

Add an address for interacting with browser websocket IPFS. (ex. `/ip4/0.0.0.0/tcp/4004/ws`) If you want to change
the websocket address port, change 4004 to other port number.

Change `DisableRelay` to **false**, and `EnableRelayHop` to **true**.

After changing IPFS configuration, restart IPFS daemon.

```
$ ipfs daemon
```

### Compile solidity codes

Compile solidity codes for generating contracts.

```
$ cd muzika-contract
$ npm install
$ truffle compile
```