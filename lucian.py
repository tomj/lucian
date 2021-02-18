import collections
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

PINATA_URL = "https://api.pinata.cloud/pinning/pinFileToIPFS"
PINATA_HEADERS = {
    "pinata_api_key": os.getenv("PINATA_API_KEY"),
    "pinata_secret_api_key": os.getenv("PINATA_SECRET_API_KEY"),
}


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


def upload_file_to_pinata(filename):
    files = {"file": open(filename, "rb")}
    response = requests.post(
        PINATA_URL, files=files, headers=PINATA_HEADERS, verify=False
    )
    asset_ipfs_hash = json.loads(response.content)["IpfsHash"]
    return asset_ipfs_hash


def upload_metadata_to_pinata(metadata):
    token_meta_bytes = json.dumps(metadata, indent=2).encode("utf-8")
    files = {"file": token_meta_bytes}
    response = requests.post(
        PINATA_URL, files=files, headers=PINATA_HEADERS, verify=False
    )
    json_ipfs_hash = json.loads(response.content)["IpfsHash"]
    return json_ipfs_hash


def mint(filename, contract, w3, name, description, mime_type):
    asset_ipfs_hash = upload_file_to_pinata(filename)
    metadata = generate_metadata(name, description, mime_type)
    metadata_ipfs_hash = upload_metadata_to_pinata(metadata)
    token_uri = f"https://ipfs.io/ipfs/{asset_ipfs_hash}"
    metadata_uri = f"https://ipfs.io/ipfs/{metadata_ipfs_hash}"

    print(token_uri)
    print(metadata_uri)

    content_hash = content_sha(filename).digest()
    metadata_hash = metadata_sha(metadata_sha).digest()

    print(content_hash)
    print(metadata_hash)

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


def generate_metadata(
    name, description, mime_type, thumbnail_ipfs_cid=None, version="zora-20210101"
):
    metadata = {
        "name": name,
        "description": description,
        "version": version,
        "mimeType": mime_type,
    }
    if thumbnail_ipfs_cid:
        metadata["thumbnailCID"] = thumbnail_ipfs_cid
    metadata = collections.OrderedDict(sorted(metadata.items()))
    return metadata


def content_sha(filename):
    BLOCK_SIZE = 65536
    content_sha = sha256()
    with open(filename, "rb") as f:
        fb = f.read(BLOCK_SIZE)
        while len(fb) > 0:
            content_sha.update(fb)
            fb = f.read(BLOCK_SIZE)
    return content_sha


def metadata_sha(metadata):
    metadata_sha = sha256(json.dumps(metadata, separators=(",", ":")).encode("utf-8"))
    return metadata_sha


if __name__ == "__main__":
    main()
