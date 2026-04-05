def generate_conf(proxy_port: int = 50000, os_type: str = "almalinux") -> str:
    """マニュアル準拠のsquid.confを返す。os_typeに応じてauth_paramのパスを切り替え"""
    if os_type == "ubuntu":
        auth_program = "/usr/lib/squid/basic_ncsa_auth"
    elif os_type == "centos6":
        auth_program = "/usr/lib64/squid/ncsa_auth"
    else:
        # almalinux, rockylinux, centos_stream
        auth_program = "/usr/lib64/squid/basic_ncsa_auth"

    return f"""\
#
# Recommended minimum configuration:
#
acl manager proto cache_object
acl localhost src 127.0.0.1/32 ::1
acl to_localhost dst 127.0.0.0/8 0.0.0.0/32 ::1

acl localnet src 10.0.0.0/8
acl localnet src 172.16.0.0/12
acl localnet src 192.168.0.0/16
acl localnet src fc00::/7
acl localnet src fe80::/10

acl SSL_ports port 443
acl SSL_ports port 80
acl Safe_ports port 80
acl Safe_ports port 21
acl Safe_ports port 443
acl Safe_ports port 70
acl Safe_ports port 210
acl Safe_ports port 1025-65535
acl Safe_ports port 280
acl Safe_ports port 488
acl Safe_ports port 591
acl Safe_ports port 777
acl CONNECT method CONNECT

# Basic Auth
auth_param basic program {auth_program} /etc/squid/.htpasswd
auth_param basic children 5
auth_param basic realm Squid Basic Authentication
auth_param basic credentialsttl 5 hours
acl password proxy_auth REQUIRED
http_access allow password

http_access allow manager localhost
http_access deny manager
http_access deny !Safe_ports
http_access deny CONNECT !SSL_ports
http_access allow localnet
http_access allow localhost
http_access deny all

http_port {proxy_port}

coredump_dir /var/spool/squid

refresh_pattern ^ftp:           1440    20%     10080
refresh_pattern ^gopher:        1440    0%      1440
refresh_pattern -i (/cgi-bin/|\\?) 0     0%      0
refresh_pattern .               0       20%     4320

# for anonymous proxy server
visible_hostname unknown
forwarded_for off
request_header_access X-FORWARDED-FOR deny all
request_header_access Via deny all
request_header_access Cache-Control deny all
"""
