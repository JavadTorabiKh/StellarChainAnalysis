import asyncio
import websockets
import json
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
import ssl

from src.core.stellar_client import StellarHorizonClient, StellarTransaction

logger = logging.getLogger(__name__)


class HorizonWebSocketListener:
    """گوش‌دهنده WebSocket برای دریافت لحظه‌ای تراکنش‌ها"""
    
    def __init__(self, horizon_url: str = "https://horizon.stellar.org"):
        self.horizon_url = horizon_url
        self.ws_url = horizon_url.replace("https://", "wss://").replace("http://", "ws://")
        self.websocket = None
        self.running = False
        self.callbacks = []
        self.reconnect_delay = 5
        
    def add_callback(self, callback: Callable):
        """افزودن callback برای پردازش تراکنش‌ها"""
        self.callbacks.append(callback)
        
    async def connect(self):
        """اتصال به WebSocket Horizon"""
        try:
            # اتصال به WebSocket
            self.websocket = await websockets.connect(
                f"{self.ws_url}/transactions",
                ssl=ssl.create_default_context() if self.ws_url.startswith("wss") else None
            )
            logger.info("Connected to Horizon WebSocket")
            return True
        except Exception as e:
            logger.error(f"Error connecting to WebSocket: {e}")
            return False
            
    async def listen(self):
        """گوش دادن به تراکنش‌ها"""
        self.running = True
        
        while self.running:
            try:
                if not self.websocket:
                    if not await self.connect():
                        await asyncio.sleep(self.reconnect_delay)
                        continue
                        
                async for message in self.websocket:
                    if not self.running:
                        break
                        
                    try:
                        data = json.loads(message)
                        
                        if data.get("type") == "transaction":
                            await self._process_transaction(data)
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"Error decoding JSON: {e}")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"WebSocket connection closed: {e}")
                self.websocket = None
                await asyncio.sleep(self.reconnect_delay)
            except Exception as e:
                logger.error(f"Error in listen loop: {e}")
                self.websocket = None
                await asyncio.sleep(self.reconnect_delay)
                
    async def _process_transaction(self, data: Dict):
        """پردازش تراکنش دریافتی"""
        try:
            # استخراج داده‌های تراکنش
            tx_data = data.get("transaction", {})
            
            # ایجاد شیء تراکنش
            client = StellarHorizonClient(self.horizon_url)
            
            # پردازش در صورت وجود callbackها
            for callback in self.callbacks:
                try:
                    await callback(tx_data)
                except Exception as e:
                    logger.error(f"Error in callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing transaction: {e}")
            
    async def stop(self):
        """توقف گوش‌دهنده"""
        self.running = False
        if self.websocket:
            await self.websocket.close()


class BatchTransactionProcessor:
    """پردازش batch تراکنش‌ها"""
    
    def __init__(self, horizon_url: str = "https://horizon.stellar.org"):
        self.client = StellarHorizonClient(horizon_url)
        self.batch_size = 100
        
    async def fetch_historical_transactions(self, start_ledger: int, 
                                          end_ledger: int = None) -> List[StellarTransaction]:
        """دریافت تراکنش‌های تاریخی"""
        all_transactions = []
        
        if not end_ledger:
            current_ledger = await self.client.get_ledger_sequence()
            if current_ledger:
                end_ledger = current_ledger
            else:
                end_ledger = start_ledger + 1000
                
        logger.info(f"Fetching transactions from ledger {start_ledger} to {end_ledger}")
        
        for ledger_seq in range(start_ledger, end_ledger + 1):
            try:
                transactions = await self.client.get_transactions_in_ledger(ledger_seq)
                all_transactions.extend(transactions)
                
                if ledger_seq % 100 == 0:
                    logger.info(f"Processed ledger {ledger_seq}/{end_ledger}")
                    
                # تاخیر برای جلوگیری از rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error fetching ledger {ledger_seq}: {e}")
                continue
                
        return all_transactions
        
    async def fetch_transactions_by_time(self, start_time: datetime, 
                                       end_time: datetime = None) -> List[StellarTransaction]:
        """دریافت تراکنش‌ها بر اساس بازه زمانی"""
        if not end_time:
            end_time = datetime.utcnow()
            
        all_transactions = []
        cursor = None
        
        while True:
            try:
                url = f"{self.client.horizon_url}/transactions"
                params = {"limit": 200, "order": "asc"}
                if cursor:
                    params["cursor"] = cursor
                    
                async with self.client.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        records = data.get("_embedded", {}).get("records", [])
                        
                        if not records:
                            break
                            
                        for tx_data in records:
                            tx = self.client._parse_transaction(tx_data)
                            if tx:
                                if tx.created_at >= start_time and tx.created_at <= end_time:
                                    all_transactions.append(tx)
                                elif tx.created_at > end_time:
                                    return all_transactions
                                    
                        # به‌روزرسانی cursor
                        last_tx = records[-1]
                        cursor = last_tx.get("paging_token")
                        
                        # بررسی زمان آخرین تراکنش
                        last_tx_time = self.client._parse_transaction(last_tx).created_at
                        if last_tx_time > end_time:
                            break
                            
                        await asyncio.sleep(0.1)
                    else:
                        break
                        
            except Exception as e:
                logger.error(f"Error in fetch_transactions_by_time: {e}")
                break
                
        return all_transactions


async def main_listener_example():
    """مثال استفاده از گوش‌دهنده"""
    
    async def process_transaction(tx_data: Dict):
        """تابع پردازش تراکنش"""
        print(f"New transaction: {tx_data.get('hash')}")
        print(f"Source: {tx_data.get('source_account')}")
        print(f"Ledger: {tx_data.get('ledger')}")
        print("-" * 50)
        
    # ایجاد گوش‌دهنده
    listener = HorizonWebSocketListener()
    listener.add_callback(process_transaction)
    
    # شروع گوش دادن
    print("Starting Horizon listener...")
    await listener.listen()


if __name__ == "__main__":
    asyncio.run(main_listener_example())