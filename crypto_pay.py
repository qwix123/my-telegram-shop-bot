# crypto_pay.py

import aiohttp
from config import CRYPTOBOT_TOKEN, CRYPTOBOT_API_URL, BYN_TO_USD


async def create_invoice(amount_byn: float, order_id: int, description: str) -> dict:
    """
    Создаёт инвойс в CryptoBot.
    Конвертирует BYN в USD.
    Возвращает ссылку на оплату.
    """
    amount_usd = round(amount_byn * BYN_TO_USD, 2)

    # Минимальная сумма в CryptoBot — 1 USD
    if amount_usd < 1:
        amount_usd = 1.0

    headers = {
        "Crypto-Pay-API-Token": CRYPTOBOT_TOKEN
    }

    payload = {
        "currency_type": "fiat",
        "fiat": "USD",
        "amount": str(amount_usd),
        "description": f"Заказ #{order_id}: {description}",
        "payload": str(order_id),
        "expires_in": 3600,  # 1 час на оплату
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{CRYPTOBOT_API_URL}/createInvoice",
                headers=headers,
                json=payload
            ) as response:
                data = await response.json()

                if data.get("ok"):
                    result = data["result"]
                    return {
                        "success": True,
                        "invoice_id": result["invoice_id"],
                        "pay_url": result["mini_app_invoice_url"],
                        "amount_usd": amount_usd,
                        "amount_byn": amount_byn,
                        "status": result["status"]
                    }
                else:
                    return {
                        "success": False,
                        "error": data.get("error", {}).get("name", "Unknown error")
                    }
    except Exception as ex:
        return {
            "success": False,
            "error": str(ex)
        }


async def check_invoice(invoice_id: int) -> dict:
    """Проверяет статус инвойса"""
    headers = {
        "Crypto-Pay-API-Token": CRYPTOBOT_TOKEN
    }

    params = {
        "invoice_ids": str(invoice_id)
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{CRYPTOBOT_API_URL}/getInvoices",
                headers=headers,
                params=params
            ) as response:
                data = await response.json()

                if data.get("ok") and data["result"]["items"]:
                    invoice = data["result"]["items"][0]
                    return {
                        "success": True,
                        "status": invoice["status"],
                        "paid": invoice["status"] == "paid"
                    }
                return {"success": False, "error": "Invoice not found"}
    except Exception as ex:
        return {"success": False, "error": str(ex)}