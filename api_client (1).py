import json
import os
import time

import requests
from requests.auth import HTTPBasicAuth
from rich.console import Console

from wbes.config import BASE_URL

console = Console()


def fetch_wbes_schedule(qca_name: str, date_str: str, rev_no: str, plants: list[str]) -> dict:
    """
    Query the POSOCO API with Basic Auth, API key header, and retries.
    Returns a dict with ``status`` and either ``data`` or error fields.
    """
    username = os.getenv(f"{qca_name}_USERNAME")
    password = os.getenv(f"{qca_name}_PASSWORD")
    api_key = os.getenv(f"{qca_name}_API_KEY")

    if not username or not password or not api_key:
        return {
            "status": "CONFIG_ERROR",
            "message": (
                f"Missing credentials in .env for QCA: {qca_name}. "
                "Please check your environment configuration."
            ),
        }

    url = f"{BASE_URL}/reports/1.0/WebAccessAPI/GetUtilityExternalSharedData"
    payload = {
        "Date": date_str,
        "SchdRevNo": int(rev_no),
        "UserName": username,
        "UtilAcronymList": plants,
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/xml",
        "X-API-Key": api_key,
    }

    max_retries = 3
    backoff_factor = 2

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                url,
                data=json.dumps(payload),
                headers=headers,
                auth=HTTPBasicAuth(username, password),
                timeout=25,
            )

            if response.status_code == 200:
                data = response.json()
                status_block = data.get("ResponseStatus", {})
                code = status_block.get("Code")

                if code in ("WBES200", "WBES-200"):
                    return {"status": "SUCCESS", "data": data}
                return {
                    "status": "API_LEVEL_ERROR",
                    "code": code,
                    "message": status_block.get("Message"),
                    "details": status_block.get("DetailsList"),
                }

            if response.status_code == 404:
                body_text = response.text
                if "No client found" in body_text or "client" in body_text.lower():
                    return _ip_blocked_result(body_text)
                return {"status": "HTTP_ERROR", "code": 404, "message": body_text}

            if response.status_code in (401, 403):
                return {
                    "status": "CREDENTIALS_REJECTED",
                    "code": response.status_code,
                    "message": (
                        "Gateway authentication rejected. Please double-check your "
                        "Username and Password in the .env file."
                    ),
                }

            return {
                "status": "HTTP_ERROR",
                "code": response.status_code,
                "message": f"Server returned error code {response.status_code}.",
                "raw_response": response.text,
            }

        except requests.exceptions.Timeout:
            console.print(
                f"[yellow][!] Attempt {attempt}: Timeout occurred. "
                "Server did not respond within 25s.[/yellow]"
            )
        except requests.exceptions.ConnectionError as conn_err:
            err_str = str(conn_err)
            is_reset = any(
                x in err_str
                for x in [
                    "10054",
                    "forcibly closed",
                    "Connection reset",
                    "Connection aborted",
                    "ConnectionRefusedError",
                ]
            )
            if is_reset:
                return _ip_blocked_result(
                    err_str,
                    message=(
                        "GRID-INDIA Gateway forcibly closed the connection during SSL "
                        "handshake (Connection Reset)."
                    ),
                    diagnostics_extra=(
                        "The central scheduling gateway is configured to instantly abort "
                        "connections from unauthorized IP addresses during the SSL handshake."
                    ),
                )
            console.print(
                f"[yellow][!] Attempt {attempt}: Connection failed. "
                "Check your DNS and network connection.[/yellow]"
            )
        except Exception as ex:
            console.print(f"[yellow][!] Attempt {attempt}: Unexpected request failure: {ex}[/yellow]")

        if attempt < max_retries:
            sleep_time = backoff_factor**attempt
            console.print(f"[dim cyan]  -> Retrying in {sleep_time} seconds...[/dim cyan]")
            time.sleep(sleep_time)

    return {
        "status": "GATEWAY_TIMEOUT",
        "message": (
            "Failed to connect to the energy grid gateway at gateway.grid-india.in "
            f"after {max_retries} attempts."
        ),
    }


def _public_ip() -> str:
    try:
        return requests.get("https://ifconfig.me", timeout=3).text.strip()
    except Exception:
        return "Unknown IP"


def _ip_blocked_result(
    raw_response: str,
    message: str = "GRID-INDIA Gateway rejected your connection.",
    diagnostics_extra: str = "",
) -> dict:
    public_ip = _public_ip()
    diagnostics = (
        f"Your public IP address [bold yellow]{public_ip}[/bold yellow] is likely "
        "not whitelisted in POSOCO's gateway firewall, or this API Key is locked to a different IP."
    )
    if diagnostics_extra:
        diagnostics = (
            f"Your public IP address [bold yellow]{public_ip}[/bold yellow] is not whitelisted "
            "in GRID-INDIA/POSOCO's gateway firewall.\n" + diagnostics_extra
        )
    return {
        "status": "IP_WHITELIST_BLOCKED",
        "message": message,
        "diagnostics": diagnostics,
        "raw_response": raw_response,
    }
