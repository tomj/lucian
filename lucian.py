import json
import math
import os
from hashlib import sha256

import requests
from dotenv import load_dotenv
from eth_account import Account
from hdwallet import HDWallet
from hdwallet.cryptocurrencies import EthereumMainnet
from web3 import Web3
from web3.middleware import construct_sign_and_send_raw_middleware, geth_poa_middleware

load_dotenv()


def main():
    account = Account.from_key(get_private_key())
    w3 = Web3(Web3.WebsocketProvider(os.getenv("INFURA_URL")))
    if os.getenv("USE_MAINNET") and int(os.getenv("USE_MAINNET")):
        contract_address = os.getenv("ZORA_CONTRACT_ADDRESS_MAINNET")
    else:
        contract_address = os.getenv("ZORA_CONTRACT_ADDRESS_RINKEBY")
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    w3.middleware_onion.add(construct_sign_and_send_raw_middleware(account))
    w3.eth.default_account = account.address
    contract = w3.eth.contract(address=contract_address, abi=get_abi())
    mint(os.getenv("FILENAME"), contract, w3)


def mint(filename, contract, w3):
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    headers = {
        "pinata_api_key": os.getenv("PINATA_API_KEY"),
        "pinata_secret_api_key": os.getenv("PINATA_SECRET_API_KEY"),
    }
    files = {"file": open(filename, "rb")}
    response = requests.post(url, files=files, headers=headers, verify=False)
    asset_ipfs_hash = json.loads(response.content)["IpfsHash"]

    # TODO: make this compliant with metadata schema concepts at
    #       https://zora.engineering/protocol/smart-contracts and
    #       https://github.com/ourzora/media-metadata-schemas
    token_meta = {
        "asset_ipfs_hash": asset_ipfs_hash,
        "convenience_asset_url": f"https://ipfs.io/ipfs/{asset_ipfs_hash}",
    }
    token_meta_bytes = json.dumps(token_meta, indent=2).encode("utf-8")
    files = {"file": token_meta_bytes}
    response = requests.post(url, files=files, headers=headers, verify=False)
    json_ipfs_hash = json.loads(response.content)["IpfsHash"]

    token_uri = f"https://ipfs.io/ipfs/{asset_ipfs_hash}"
    metadata_uri = f"https://ipfs.io/ipfs/{json_ipfs_hash}"

    print(token_uri)
    print(metadata_uri)

    BLOCK_SIZE = 65536

    content_sha = sha256()
    with open(filename, "rb") as f:
        fb = f.read(BLOCK_SIZE)
        while len(fb) > 0:
            content_sha.update(fb)
            fb = f.read(BLOCK_SIZE)

    content_sha = content_sha.digest()
    metadata_sha = sha256(json.dumps(token_meta).encode("utf-8")).digest()

    print(content_sha)
    print(metadata_sha)

    share = math.pow(10, 18)
    share = int(share * 100)
    zora_data = {
        "tokenURI": token_uri,
        "metadataURI": metadata_uri,
        "contentHash": content_sha,
        "metadataHash": metadata_sha,
    }
    zora_bidshares = {
        "prevOwner": {"value": 0},
        "creator": {"value": 0},
        "owner": {"value": share},
    }

    print(zora_data)
    print(zora_bidshares)

    gas_estimate = contract.functions.mint(
        data=zora_data, bidShares=zora_bidshares
    ).estimateGas({"from": w3.eth.default_account})
    # tx_hash = contract.functions.mint(
    #     data=zora_data, bidShares=zora_bidshares
    # ).transact()
    # receipt = w3.eth.waitForTransactionReceipt(tx_hash)

    print(gas_estimate)
    # print(tx_hash)
    # print(receipt)


def get_abi():
    with open("abi.json", "r") as abi_file:
        abi = json.load(abi_file)
        return abi


def get_private_key():
    MNEMONIC = os.getenv("MNEMONIC")
    LANGUAGE = "english"
    PASSPHRASE = None
    hdwallet: HDWallet = HDWallet(cryptocurrency=EthereumMainnet)
    hdwallet.from_mnemonic(mnemonic=MNEMONIC, passphrase=PASSPHRASE, language=LANGUAGE)
    hdwallet.from_path(
        path=EthereumMainnet.BIP44_PATH.format(account=0, change=0, address=0)
    )
    private_key = f"0x{hdwallet.private_key()}"
    hdwallet.clean_derivation()
    return private_key


if __name__ == "__main__":
    main()
