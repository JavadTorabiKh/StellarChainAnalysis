import asyncio
import aiohttp
import json
from typing import Dict, List, Optional, AsyncGenerator
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from stellar_sdk import Server, Network
from stellar_sdk.exceptions import NotFoundError, BadRequestError

logger = logging.getLogger(__name__)


@dataclass
class StellarTransaction:
    """مدل داده تراکنش استلار"""
    hash: str
    ledger: int
    created_at: datetime
    source_account: str
    fee_paid: int
    operation_count: int
    memo: Optional[str] = None
    memo_type: Optional[str] = None
    successful: bool = True
    envelope_xdr: Optional[str] = None
    result_xdr: Optional[str] = None
    result_meta_xdr: Optional[str] = None
    fee_meta_xdr: Optional[str] = None
    signatures: List[str] = None
    paging_token: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "hash": self.hash,
            "ledger": self.ledger,
            "created_at": self.created_at.isoformat(),
            "source_account": self.source_account,
            "fee_paid": self.fee_paid,
            "operation_count": self.operation_count,
            "memo": self.memo,
            "memo_type": self.memo_type,
            "successful": self.successful,
            "paging_token": self.paging_token
        }


@dataclass
class StellarOperation:
    """مدل داده عملیات"""
    id: str
    transaction_hash: str
    source_account: str
    type: str
    created_at: datetime
    details: Dict
    paging_token: str


@dataclass
class StellarAccount:
    """مدل داده حساب"""
    account_id: str
    sequence: int
    balance: str
    subentry_count: int
    home_domain: Optional[str] = None
    inflation_destination: Optional[str] = None
    thresholds: Dict = None
    flags: Dict = None
    signers: List[Dict] = None
    data: Dict = None


class StellarHorizonClient:
    """کلاینت برای ارتباط با Horizon API"""
    
    def __init__(self, horizon_url: str = "https://horizon.stellar.org", 
                 network_passphrase: str = None):
        self.horizon_url = horizon_url
        self.server = Server(horizon_url=horizon_url)
        
        if network_passphrase:
            Network(network_passphrase)
            
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def connect(self):
        """ایجاد session برای ارتباط async"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
            
    async def close(self):
        """بستن session"""
        if self.session:
            await self.session.close()
            self.session = None
            
    async def get_account(self, account_id: str) -> Optional[StellarAccount]:
        """دریافت اطلاعات یک حساب"""
        try:
            async with self.session.get(
                f"{self.horizon_url}/accounts/{account_id}"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_account(data)
                elif response.status == 404:
                    logger.warning(f"Account not found: {account_id}")
                    return None
                else:
                    logger.error(f"Error fetching account: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error in get_account: {e}")
            return None
            
    async def get_transaction(self, tx_hash: str) -> Optional[StellarTransaction]:
        """دریافت اطلاعات یک تراکنش"""
        try:
            async with self.session.get(
                f"{self.horizon_url}/transactions/{tx_hash}"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_transaction(data)
                else:
                    logger.error(f"Error fetching transaction: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error in get_transaction: {e}")
            return None
            
    async def get_transactions_for_account(self, account_id: str, 
                                          limit: int = 100,
                                          cursor: str = None) -> List[StellarTransaction]:
        """دریافت تراکنش‌های یک حساب"""
        transactions = []
        try:
            url = f"{self.horizon_url}/accounts/{account_id}/transactions"
            params = {"limit": limit, "order": "desc"}
            if cursor:
                params["cursor"] = cursor
                
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    for tx_data in data.get("_embedded", {}).get("records", []):
                        tx = self._parse_transaction(tx_data)
                        if tx:
                            transactions.append(tx)
        except Exception as e:
            logger.error(f"Error in get_transactions_for_account: {e}")
            
        return transactions
        
    async def stream_transactions(self, cursor: str = "now") -> AsyncGenerator[StellarTransaction, None]:
        """جریان زنده تراکنش‌ها از Horizon"""
        url = f"{self.horizon_url}/transactions"
        params = {"cursor": cursor, "order": "asc"}
        
        while True:
            try:
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        records = data.get("_embedded", {}).get("records", [])
                        
                        for tx_data in records:
                            tx = self._parse_transaction(tx_data)
                            if tx:
                                yield tx
                                
                        # به‌روزرسانی cursor برای دریافت بعدی
                        if records:
                            last_tx = records[-1]
                            params["cursor"] = last_tx.get("paging_token")
                            
                        # تاخیر برای جلوگیری از rate limiting
                        await asyncio.sleep(0.1)
                    else:
                        logger.error(f"Error in stream: {response.status}")
                        await asyncio.sleep(5)
                        
            except Exception as e:
                logger.error(f"Error in stream_transactions: {e}")
                await asyncio.sleep(5)
                
    async def stream_ledgers(self, cursor: str = "now") -> AsyncGenerator[Dict, None]:
        """جریان زنده ledgerها"""
        url = f"{self.horizon_url}/ledgers"
        params = {"cursor": cursor, "order": "asc"}
        
        while True:
            try:
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        records = data.get("_embedded", {}).get("records", [])
                        
                        for ledger in records:
                            yield ledger
                            
                        if records:
                            last_ledger = records[-1]
                            params["cursor"] = last_ledger.get("paging_token")
                            
                        await asyncio.sleep(0.5)
                    else:
                        logger.error(f"Error streaming ledgers: {response.status}")
                        await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error in stream_ledgers: {e}")
                await asyncio.sleep(5)
                
    async def get_operations_for_transaction(self, tx_hash: str) -> List[StellarOperation]:
        """دریافت عملیات‌های یک تراکنش"""
        operations = []
        try:
            url = f"{self.horizon_url}/transactions/{tx_hash}/operations"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    for op_data in data.get("_embedded", {}).get("records", []):
                        operation = self._parse_operation(op_data)
                        if operation:
                            operations.append(operation)
        except Exception as e:
            logger.error(f"Error in get_operations_for_transaction: {e}")
            
        return operations
        
    async def get_payments(self, account_id: str = None, 
                          limit: int = 100,
                          cursor: str = None) -> List[Dict]:
        """دریافت پرداخت‌ها"""
        payments = []
        try:
            url = f"{self.horizon_url}/payments"
            params = {"limit": limit, "order": "desc"}
            
            if account_id:
                url = f"{self.horizon_url}/accounts/{account_id}/payments"
                
            if cursor:
                params["cursor"] = cursor
                
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    payments = data.get("_embedded", {}).get("records", [])
        except Exception as e:
            logger.error(f"Error in get_payments: {e}")
            
        return payments
        
    async def get_ledger_sequence(self) -> Optional[int]:
        """دریافت آخرین sequence ledger"""
        try:
            url = f"{self.horizon_url}/ledgers"
            params = {"order": "desc", "limit": 1}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    records = data.get("_embedded", {}).get("records", [])
                    if records:
                        return records[0].get("sequence")
        except Exception as e:
            logger.error(f"Error in get_ledger_sequence: {e}")
            
        return None
        
    async def get_transactions_in_ledger(self, ledger_sequence: int) -> List[StellarTransaction]:
        """دریافت تراکنش‌های یک ledger خاص"""
        transactions = []
        try:
            url = f"{self.horizon_url}/ledgers/{ledger_sequence}/transactions"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    for tx_data in data.get("_embedded", {}).get("records", []):
                        tx = self._parse_transaction(tx_data)
                        if tx:
                            transactions.append(tx)
        except Exception as e:
            logger.error(f"Error in get_transactions_in_ledger: {e}")
            
        return transactions
        
    async def batch_get_accounts(self, account_ids: List[str]) -> Dict[str, Optional[StellarAccount]]:
        """دریافت batch اطلاعات حساب‌ها"""
        accounts = {}
        tasks = []
        
        for account_id in account_ids:
            task = self.get_account(account_id)
            tasks.append((account_id, task))
            
        for account_id, task in tasks:
            try:
                account = await task
                accounts[account_id] = account
            except Exception as e:
                logger.error(f"Error fetching account {account_id}: {e}")
                accounts[account_id] = None
                
        return accounts
        
    def _parse_transaction(self, tx_data: Dict) -> Optional[StellarTransaction]:
        """تبدیل داده JSON به شیء تراکنش"""
        try:
            created_at = datetime.fromisoformat(tx_data["created_at"].replace("Z", "+00:00"))
            
            return StellarTransaction(
                hash=tx_data["hash"],
                ledger=tx_data["ledger"],
                created_at=created_at,
                source_account=tx_data["source_account"],
                fee_paid=int(tx_data["fee_paid"]),
                operation_count=int(tx_data["operation_count"]),
                memo=tx_data.get("memo"),
                memo_type=tx_data.get("memo_type"),
                successful=tx_data.get("successful", True),
                envelope_xdr=tx_data.get("envelope_xdr"),
                result_xdr=tx_data.get("result_xdr"),
                result_meta_xdr=tx_data.get("result_meta_xdr"),
                fee_meta_xdr=tx_data.get("fee_meta_xdr"),
                signatures=tx_data.get("signatures", []),
                paging_token=tx_data.get("paging_token")
            )
        except Exception as e:
            logger.error(f"Error parsing transaction: {e}")
            return None
            
    def _parse_account(self, account_data: Dict) -> StellarAccount:
        """تبدیل داده JSON به شیء حساب"""
        return StellarAccount(
            account_id=account_data["account_id"],
            sequence=int(account_data["sequence"]),
            balance=account_data["balances"][0]["balance"] if account_data["balances"] else "0",
            subentry_count=int(account_data["subentry_count"]),
            home_domain=account_data.get("home_domain"),
            inflation_destination=account_data.get("inflation_destination"),
            thresholds=account_data.get("thresholds", {}),
            flags=account_data.get("flags", {}),
            signers=account_data.get("signers", []),
            data=account_data.get("data", {})
        )
        
    def _parse_operation(self, op_data: Dict) -> Optional[StellarOperation]:
        """تبدیل داده JSON به شیء عملیات"""
        try:
            created_at = datetime.fromisoformat(op_data["created_at"].replace("Z", "+00:00"))
            
            return StellarOperation(
                id=op_data["id"],
                transaction_hash=op_data["transaction_hash"],
                source_account=op_data["source_account"],
                type=op_data["type"],
                created_at=created_at,
                details=op_data,
                paging_token=op_data.get("paging_token")
            )
        except Exception as e:
            logger.error(f"Error parsing operation: {e}")
            return None