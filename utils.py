from ipaddress import ip_address


def is_host_ip_address(host: str):
    try:
        host = ip_address(host)
        if host:
            return True
    except ValueError:
        return False