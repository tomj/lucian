## Lucian: mint Zora NFT's using Python

![Banner](lucian.jpg)

### Overview

Lucian is a basic Python application which uploads an image to IPFS using [Piñata](https://pinata.cloud) and then uses that uploaded image to mint an ECR-721 NFT based on the [Zora protocol](https://zora.engineering/protocol). To date this has only been tested on the Rinkeby testnet.

### Usage

0. Sign up for accounts at [Piñata](https://pinata.cloud) and [Infura](https://infura.io)
1. Rename `.env.example` to `.env` and set the environment variables to the appropriate values
2. Call Lucian:

```shell
$ python ./lucian.py
```

### TODO:

- make this a proper CLI app which takes filename argument from command link invocation
- write some proper tests
- test this on mainnet
