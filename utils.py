from ipaddress import ip_address
from dataclasses import dataclass

def is_host_ip_address(host: str):
    try:
        host = ip_address(host)
        if host:
            return True
    except ValueError:
        return False

@dataclass
class DeviceCredential:
    username: str = ''
    password: str = ''

@dataclass
class NetworkDevice:
    host: str
    domain_suffix: str = ''
    credential: DeviceCredential = None
