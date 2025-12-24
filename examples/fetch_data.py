#!/usr/bin/env python3
"""
مثال عملی برای دریافت داده از بلاکچین استلار
"""

import os
import sys
import asyncio
from datetime import datetime

# اضافه کردن مسیر parent به sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# اکنون می‌توانیم import کنیم
try:
    from src.core.stellar_client import StellarHorizonClient
    from src.streaming.horizon_listener import HorizonWebSocketListener, BatchTransactionProcessor
    print("✅ ماژول‌ها با موفقیت import شدند")
except ImportError as e:
    print(f"❌ خطای import: {e}")
    print("📁 مسیرهای sys.path:")
    for path in sys.path:
        print(f"  - {path}")
    sys.exit(1)


async def example_fetch_account():
    """مثال دریافت اطلاعات حساب"""
    print("📋 مثال ۱: دریافت اطلاعات حساب")
    print("-" * 50)
    
    try:
        # استفاده از context manager
        async with StellarHorizonClient() as client:
            # حساب معروف Stellar Development Foundation
            account_id = "GA5XIGA5C7QTPTWXQHY6MCJRMTRZDOSHR6EFIBNDQTCQHG262N4GGKTM"
            
            print(f"🔍 در حال دریافت اطلاعات حساب: {account_id[:20]}...")
            account = await client.get_account(account_id)
            
            if account:
                print(f"✅ حساب پیدا شد!")
                print(f"   👤 آدرس: {account.account_id}")
                print(f"   💰 موجودی: {account.balance} XLM")
                print(f"   🔢 Sequence: {account.sequence}")
                print(f"   🏠 Home Domain: {account.home_domain or 'ندارد'}")
                print(f"   📊 تعداد زیرمجموعه: {account.subentry_count}")
            else:
                print("❌ حساب پیدا نشد")
    except Exception as e:
        print(f"❌ خطا در دریافت حساب: {e}")
        
    print()


async def example_fetch_transactions():
    """مثال دریافت تراکنش‌های اخیر"""
    print("📋 مثال ۲: دریافت تراکنش‌های اخیر")
    print("-" * 50)
    
    try:
        async with StellarHorizonClient() as client:
            # دریافت ۵ تراکنش آخر
            account_id = "GA5XIGA5C7QTPTWXQHY6MCJRMTRZDOSHR6EFIBNDQTCQHG262N4GGKTM"
            
            print(f"🔍 در حال دریافت تراکنش‌های حساب: {account_id[:20]}...")
            transactions = await client.get_transactions_for_account(account_id, limit=3)
            
            print(f"📊 تعداد تراکنش‌های دریافتی: {len(transactions)}")
            
            for i, tx in enumerate(transactions, 1):
                print(f"\n  {i}. تراکنش:")
                print(f"     🔗 Hash: {tx.hash[:25]}...")
                print(f"     📅 زمان: {tx.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"     💰 کارمزد: {tx.fee_paid} stroops")
                print(f"     📝 Memo: {tx.memo or 'خالی'}")
                print(f"     📒 Ledger: {tx.ledger}")
    except Exception as e:
        print(f"❌ خطا در دریافت تراکنش‌ها: {e}")
        
    print()


async def example_get_ledger_info():
    """مثال دریافت اطلاعات ledger"""
    print("📋 مثال ۳: دریافت اطلاعات ledger جاری")
    print("-" * 50)
    
    try:
        async with StellarHorizonClient() as client:
            ledger_seq = await client.get_ledger_sequence()
            if ledger_seq:
                print(f"✅ آخرین ledger: {ledger_seq}")
                
                # دریافت تراکنش‌های این ledger
                print(f"🔍 در حال دریافت تراکنش‌های ledger {ledger_seq}...")
                transactions = await client.get_transactions_in_ledger(ledger_seq)
                
                print(f"📊 تعداد تراکنش‌ها در این ledger: {len(transactions)}")
                
                if transactions:
                    # خلاصه‌ای از تراکنش‌ها
                    sources = {}
                    for tx in transactions[:5]:  # فقط ۵ تراکنش اول
                        source = tx.source_account[:10] + "..."
                        sources[source] = sources.get(source, 0) + 1
                    
                    print("\n  📈 نمونه‌ای از منابع تراکنش‌ها:")
                    for source, count in sources.items():
                        print(f"     {source}: {count} تراکنش")
            else:
                print("❌ نتوانستیم sequence ledger را دریافت کنیم")
    except Exception as e:
        print(f"❌ خطا در دریافت اطلاعات ledger: {e}")
        
    print()


async def example_simple_stream():
    """مثال ساده گوش دادن به تراکنش‌ها"""
    print("📋 مثال ۴: گوش دادن به تراکنش‌های زنده (۵ ثانیه)")
    print("-" * 50)
    
    print("⚠️  این مثال نیاز به اتصال اینترنت دارد و ممکن است چند لحظه طول بکشد...")
    
    counter = 0
    max_transactions = 3
    
    async def process_transaction(tx_data):
        nonlocal counter
        counter += 1
        
        tx_hash = tx_data.get('hash', '')[:20]
        source = tx_data.get('source_account', '')[:10]
        ledger = tx_data.get('ledger', 0)
        
        print(f"\n  🎯 تراکنش #{counter}:")
        print(f"     🔗 Hash: {tx_hash}...")
        print(f"     👤 از: {source}...")
        print(f"     📒 Ledger: {ledger}")
        
        if counter >= max_transactions:
            return True  # سیگنال توقف
        return False
    
    try:
        # ایجاد گوش‌دهنده
        listener = HorizonWebSocketListener()
        listener.add_callback(process_transaction)
        
        print("\n🎧 در حال گوش دادن به تراکنش‌های زنده...")
        print("برای خروج Ctrl+C را فشار دهید\n")
        
        # اجرا برای ۱۰ ثانیه یا تا ۳ تراکنش
        import signal
        
        class TimeoutException(Exception):
            pass
            
        def timeout_handler(signum, frame):
            raise TimeoutException()
            
        # تنظیم تایم‌اوت
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(10)
        
        try:
            await listener.listen()
        except TimeoutException:
            print("\n⏰ زمان گوش دادن به پایان رسید")
        except KeyboardInterrupt:
            print("\n⏹️ توسط کاربر متوقف شد")
        except Exception as e:
            print(f"\n❌ خطا در گوش دادن: {e}")
        finally:
            signal.alarm(0)  # غیرفعال کردن آلارم
            await listener.stop()
            
    except Exception as e:
        print(f"❌ خطا در راه‌اندازی گوش‌دهنده: {e}")
        
    print()


async def example_test_connection():
    """آزمایش اتصال به Horizon"""
    print("📋 آزمایش اتصال به شبکه استلار")
    print("-" * 50)
    
    try:
        async with StellarHorizonClient() as client:
            # تست ساده با دریافت یک حساب شناخته شده
            test_account = "GAAZI4TCR3TY5OJHCTJC2A4QSY6CJWJH5IAJTGKIN2ER7LBNVKOCCWN7"
            
            print(f"🔍 آزمایش اتصال به {client.horizon_url}...")
            
            # تست GET ساده
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(client.horizon_url) as resp:
                    if resp.status == 200:
                        print("✅ Horizon API در دسترس است")
                    else:
                        print(f"❌ Horizon پاسخ داد: {resp.status}")
            
            # تست دریافت حساب
            print(f"🔍 دریافت حساب آزمایشی...")
            account = await client.get_account(test_account)
            if account:
                print(f"✅ اتصال به بلاکچین استلار موفقیت‌آمیز بود!")
                print(f"   📍 شبکه: Stellar Public Network")
                print(f"   👤 حساب تست: {account.account_id[:20]}...")
                print(f"   💰 موجودی: {account.balance} XLM")
            else:
                print("⚠️  حساب تست پیدا نشد، اما اتصال برقرار است")
                
    except aiohttp.ClientConnectorError:
        print("❌ خطای اتصال: نمی‌توان به Horizon متصل شد")
        print("   لطفاً اتصال اینترنت خود را بررسی کنید")
    except Exception as e:
        print(f"❌ خطای ناشناخته: {e}")
        
    print()


async def main():
    """تابع اصلی"""
    print("=" * 60)
    print("🚀 Stellar Blockchain Data Fetcher - v1.0")
    print("=" * 60)
    print()
    
    try:
        # آزمایش اتصال اولیه
        await example_test_connection()
        
        # اگر اتصال برقرار بود، مثال‌های دیگر را اجرا کن
        print("🎯 اجرای مثال‌های مختلف...")
        print()
        
        await example_fetch_account()
        await example_fetch_transactions()
        await example_get_ledger_info()
        await example_simple_stream()
        
    except KeyboardInterrupt:
        print("\n\n⏹️ برنامه توسط کاربر متوقف شد")
    except Exception as e:
        print(f"\n❌ خطای غیرمنتظره: {e}")
        import traceback
        traceback.print_exc()
        
    print("\n" + "=" * 60)
    print("✅ برنامه با موفقیت به پایان رسید!")
    print("=" * 60)


if __name__ == "__main__":
    # برای ویندوز که signal.SIGALRM ندارد
    if sys.platform == "win32":
        print("⚠️  توجه: در ویندوز، تایم‌اوت سیگنال پشتیبانی نمی‌شود")
        print("   مثال گوش دادن ممکن است متفاوت کار کند")
        print()
    
    asyncio.run(main())