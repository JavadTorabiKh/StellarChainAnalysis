import json
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
import redis.asyncio as redis
from collections import defaultdict

from src.core.stellar_client import StellarTransaction
from src.streaming.horizon_listener import HorizonWebSocketListener

logger = logging.getLogger(__name__)


class TransactionProcessor:
    """پردازشگر تراکنش‌ها"""
    
    def __init__(self, redis_client: redis.Redis = None):
        self.redis = redis_client
        self.stats = defaultdict(int)
        self.last_processed = None
        self.process_callbacks = []
        
    def add_processor(self, callback: Callable):
        """افزودن پردازشگر"""
        self.process_callbacks.append(callback)
        
    async def process_transaction(self, tx_data: Dict):
        """پردازش یک تراکنش"""
        try:
            self.stats['total_received'] += 1
            self.last_processed = datetime.utcnow()
            
            # پردازش توسط همه callbackها
            for callback in self.process_callbacks:
                try:
                    await callback(tx_data)
                except Exception as e:
                    logger.error(f"Error in processor callback: {e}")
                    
            self.stats['processed'] += 1
            
            # ذخیره در Redis
            if self.redis:
                await self._store_in_redis(tx_data)
                
        except Exception as e:
            logger.error(f"Error processing transaction: {e}")
            self.stats['errors'] += 1
            
    async def _store_in_redis(self, tx_data: Dict):
        """ذخیره تراکنش در Redis"""
        try:
            tx_hash = tx_data.get('hash')
            
            # ذخیره به عنوان hash
            await self.redis.hset(
                f"tx:{tx_hash}",
                mapping={
                    'hash': tx_hash,
                    'source': tx_data.get('source_account', ''),
                    'ledger': str(tx_data.get('ledger', 0)),
                    'timestamp': datetime.utcnow().isoformat(),
                    'raw': json.dumps(tx_data)
                }
            )
            
            # اضافه کردن به لیست تراکنش‌های اخیر
            await self.redis.lpush('recent_transactions', tx_hash)
            await self.redis.ltrim('recent_transactions', 0, 999)
            
        except Exception as e:
            logger.error(f"Error storing in Redis: {e}")


class StreamManager:
    """مدیریت جریان داده‌ها"""
    
    def __init__(self, horizon_url: str = "https://horizon.stellar.org"):
        self.horizon_url = horizon_url
        self.listener = HorizonWebSocketListener(horizon_url)
        self.processor = TransactionProcessor()
        self.running = False
        
    async def start(self):
        """شروع گوش دادن و پردازش"""
        self.running = True
        
        # اضافه کردن پردازشگر
        self.listener.add_callback(self.processor.process_transaction)
        
        # شروع گوش‌دهنده
        logger.info("Starting stream manager...")
        await self.listener.listen()
        
    async def stop(self):
        """توقف سیستم"""
        self.running = False
        await self.listener.stop()
        
    def get_stats(self) -> Dict:
        """دریافت آمار"""
        return dict(self.processor.stats)