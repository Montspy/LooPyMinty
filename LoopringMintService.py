import aiohttp
from typing import TypedDict, cast
from pprint import pprint

from DataClasses import *

from hello_loopring.sdk.ethsnarks.field import SNARK_SCALAR_FIELD
from hello_loopring.sdk.ethsnarks.poseidon import poseidon_params
from hello_loopring.sdk.sig_utils.eddsa_utils import *

class NFTDataEddsaSignHelper(EddsaSignHelper):
    MAX_INPUTS: int = 6

    def __init__(self, private_key="0x1"):
        super(NFTDataEddsaSignHelper, self).__init__(
            poseidon_params = poseidon_params(SNARK_SCALAR_FIELD, self.MAX_INPUTS+1, 6, 52, b'poseidon', 5, security_target=128),
            private_key = private_key
        )

    def serialize_data(self, inputs):
        return [int(data) for data in inputs][:self.MAX_INPUTS]

class NFTEddsaSignHelper(EddsaSignHelper):
    MAX_INPUTS: int = 9

    def __init__(self, private_key="0x1"):
        super(NFTEddsaSignHelper, self).__init__(
            poseidon_params = poseidon_params(SNARK_SCALAR_FIELD, self.MAX_INPUTS+1, 6, 53, b'poseidon', 5, security_target=128),
            private_key = private_key
        )

    def serialize_data(self, inputs):
        return [int(data) for data in inputs][:self.MAX_INPUTS]

class LoopringMintService(object):
    base_url: str = "https://api3.loopring.io"
    session: aiohttp.ClientSession
    last_status: int
    last_error: dict

    def __init__(self) -> None:
        self.session = aiohttp.ClientSession(base_url=self.base_url)

    async def getNextStorageId(self, apiKey: str, accountId: int, sellTokenId: int) -> StorageId:
        params = {"accountId": accountId,
                  "sellTokenId": sellTokenId}
        headers = {"x-api-key": apiKey}
        storage_id = None

        try:
            response = await self.session.get("/api/v3/storageId", params=params, headers=headers)
            parsed = await response.json()
            self.last_status = response.status

            response.raise_for_status()
            storage_id = cast(StorageId, parsed)
        except aiohttp.ClientError as client_err:
            print(f"Error getting storage id: {client_err}")
            pprint(parsed)
            self.last_error = parsed
        except Exception as err:
            print(f"An error ocurred getting storage id: {err}")
            pprint(parsed)
            self.last_error = parsed

        return storage_id

    async def computeTokenAddress(self, apiKey: str, counterFactualNftInfo: CounterFactualNftInfo) -> CounterFactualNft:
        params = {"nftFactory": counterFactualNftInfo['nftFactory'],
                  "nftOwner": counterFactualNftInfo['nftOwner'],
                  "nftBaseUri": counterFactualNftInfo['nftBaseUri']}
        headers = {"x-api-key": apiKey}
        counterfactual_nft = None

        try:
            response = await self.session.request("get", "/api/v3/nft/info/computeTokenAddress", params=params, headers=headers)
            parsed = await response.json()
            self.last_status = response.status

            response.raise_for_status()
            counterfactual_nft = cast(CounterFactualNft, parsed)
        except aiohttp.ClientError as client_err:
            print(f"Error computing token address: {client_err}")
            pprint(parsed)
            self.last_error = parsed
        except Exception as err:
            print(f"An error ocurred computing token address: {err}")
            pprint(parsed)
            self.last_error = parsed

        return counterfactual_nft

    async def getOffChainFee(self, apiKey: str, accountId: int, requestType: int, tokenAddress: str) -> OffchainFee:
        params = {"accountId": accountId,
                  "requestType": requestType,
                  "tokenAddress": tokenAddress}
        headers = {"x-api-key": apiKey}
        off_chain_fee = None

        try:
            response = await self.session.request("get", "/api/v3/user/nft/offchainFee", params=params, headers=headers)
            parsed = await response.json()
            self.last_status = response.status

            response.raise_for_status()
            off_chain_fee = cast(OffchainFee, parsed)
        except aiohttp.ClientError as client_err:
            print(f"Error getting off chain fee: {client_err}")
            pprint(parsed)
            self.last_error = parsed
        except Exception as err:
            print(f"An error ocurred getting off chain fee: {err}")
            pprint(parsed)
            self.last_error = parsed

        return off_chain_fee

    async def getNftData(self, nftDatas: str) -> NftData:
        params = {"nftDatas": nftDatas}
        headers = {}
        nft_data = None

        try:
            response = await self.session.request("get", "/api/v3/nft/info/nfts", params=params, headers=headers)
            parsed = await response.json()
            self.last_status = response.status
            
            response.raise_for_status()
            nft_data = cast(NftData, parsed)
        except aiohttp.ClientError as client_err:
            print(f"Error getting nft datas: {client_err}")
            pprint(parsed)
            self.last_error = parsed
        except Exception as err:
            print(f"An error ocurred getting nft datas: {err}")
            pprint(parsed)
            self.last_error = parsed

        return nft_data


    async def mintNft(
            self,
            apiKey: str,
            exchange: str,
            minterId: int,
            minterAddress: str,
            toAccountId: int,
            toAddress: str,
            nftType: int,
            tokenAddress: str,
            nftId: str,
            amount: str,
            validUntil: int,
            royaltyPercentage: int,
            storageId: int,
            maxFeeTokenId: int,
            maxFeeAmount: str,
            forceToMint: bool,
            counterFactualNftInfo: CounterFactualNftInfo,
            eddsaSignature: str) -> MintResponseData:
        params = {"exchange": exchange,
                  "minterId": minterId,
                  "minterAddress": minterAddress,
                  "toAccountId": toAccountId,
                  "toAddress": toAddress,
                  "nftType": nftType,
                  "tokenAddress": tokenAddress,
                  "nftId": nftId,
                  "amount": amount,
                  "validUntil": validUntil,
                  "royaltyPercentage": royaltyPercentage,
                  "storageId": storageId,
                  "maxFee": {
                      "tokenId": maxFeeTokenId,
                      "amount": maxFeeAmount
                  },
                  "forceToMint": forceToMint,
                  "counterFactualNftInfo": {
                      "nftFactory": counterFactualNftInfo['nftFactory'],
                      "nftOwner": counterFactualNftInfo['nftOwner'],
                      "nftBaseUri": counterFactualNftInfo['nftBaseUri']
                  },
                  "eddsaSignature": eddsaSignature}
        headers = {"x-api-key": apiKey}
        nft_mint_data = None

        try:
            response = await self.session.post("/api/v3/nft/mint", json=params, headers=headers)
            parsed = await response.json()
            self.last_status = response.status

            response.raise_for_status()
            nft_mint_data = cast(MintResponseData, parsed)
        except aiohttp.ClientError as client_err:
            print("Error minting nft: ")
            pprint(client_err)
            pprint(parsed)
            self.last_error = parsed
        except Exception as err:
            print("An error ocurred minting nft: ")
            pprint(err)
            pprint(parsed)
            self.last_error = parsed

        return nft_mint_data

    async def __aenter__(self) -> 'LoopringMintService':
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.session.close()
