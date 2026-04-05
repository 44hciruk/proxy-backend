import paramiko
from squid_config import generate_conf


class SSHSetup:
    """VPSへのSSH接続とセットアップを管理"""

    def __init__(self):
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._connected = False

    def connect(self, host: str, port: int, user: str, password: str):
        self._client.connect(
            hostname=host,
            port=port,
            username=user,
            password=password,
            timeout=15,
            banner_timeout=15,
        )
        self._connected = True

    def execute(self, command: str) -> tuple[str, str]:
        if not self._connected:
            raise RuntimeError("SSH未接続")
        _stdin, stdout, stderr = self._client.exec_command(command, timeout=300)
        stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        return out, err

    def upload(self, content: str, remote_path: str):
        if not self._connected:
            raise RuntimeError("SSH未接続")
        sftp = self._client.open_sftp()
        try:
            with sftp.file(remote_path, "w") as f:
                f.write(content)
        finally:
            sftp.close()

    def close(self):
        if self._connected:
            self._client.close()
            self._connected = False

    # ── OS別セットアップ手順 ──

    def get_steps(self, os_type: str, proxy_user: str, proxy_password: str, proxy_port: int):
        """os_typeに応じたセットアップステップのジェネレータを返す"""
        if os_type == "centos6":
            yield from self._steps_centos6(proxy_user, proxy_password, proxy_port)
        elif os_type == "ubuntu":
            yield from self._steps_ubuntu(proxy_user, proxy_password, proxy_port)
        else:
            # almalinux, rockylinux, centos_stream
            yield from self._steps_rhel(proxy_user, proxy_password, proxy_port, os_type)

    def _steps_centos6(self, proxy_user, proxy_password, proxy_port):
        # 1. install
        yield "squidインストール中...", "running"
        self.execute("yum install -y nano squid")
        yield "squidインストール完了", "ok"

        # 2. clean
        yield "yum clean all...", "running"
        self.execute("yum clean all")
        yield "yum clean all 完了", "ok"

        # 3. squid.conf
        yield "squid.conf アップロード中...", "running"
        self.execute("cp /etc/squid/squid.conf /etc/squid/squid.conf.orig")
        conf = generate_conf(proxy_port, "centos6")
        self.upload(conf, "/etc/squid/squid.conf")
        yield "squid.conf アップロード完了", "ok"

        # 4. htpasswd
        yield f"htpasswd ユーザー作成中: {proxy_user}", "running"
        self.execute(f"htpasswd -cb /etc/squid/.htpasswd {proxy_user} {proxy_password}")
        yield "htpasswd ユーザー作成完了", "ok"

        # 5. start
        yield "Squid 起動中...", "running"
        self.execute("/usr/sbin/squid start")
        self.execute("/etc/rc.d/init.d/squid start")
        yield "Squid 起動完了", "ok"

        # 6. autostart
        yield "自動起動設定中...", "running"
        self.execute("chkconfig squid on")
        yield "自動起動設定完了", "ok"

    def _steps_rhel(self, proxy_user, proxy_password, proxy_port, os_type):
        # 1. install
        yield "squidインストール中...", "running"
        self.execute("dnf install -y squid httpd-tools")
        yield "squidインストール完了", "ok"

        # 2. clean
        yield "dnf clean all...", "running"
        self.execute("dnf clean all")
        yield "dnf clean all 完了", "ok"

        # 3. squid.conf
        yield "squid.conf アップロード中...", "running"
        self.execute("cp /etc/squid/squid.conf /etc/squid/squid.conf.orig")
        conf = generate_conf(proxy_port, os_type)
        self.upload(conf, "/etc/squid/squid.conf")
        yield "squid.conf アップロード完了", "ok"

        # 4. htpasswd
        yield f"htpasswd ユーザー作成中: {proxy_user}", "running"
        self.execute(f"htpasswd -cb /etc/squid/.htpasswd {proxy_user} {proxy_password}")
        yield "htpasswd ユーザー作成完了", "ok"

        # 5. firewall
        yield "ファイアウォール設定中...", "running"
        self.execute("systemctl enable firewalld")
        self.execute("systemctl start firewalld")
        self.execute(f"firewall-cmd --permanent --add-port={proxy_port}/tcp")
        self.execute("firewall-cmd --reload")
        yield "ファイアウォール設定完了", "ok"

        # 6. start
        yield "Squid 起動中...", "running"
        self.execute("systemctl start squid")
        yield "Squid 起動完了", "ok"

        # 7. autostart
        yield "自動起動設定中...", "running"
        self.execute("systemctl enable squid")
        yield "自動起動設定完了", "ok"

    def _steps_ubuntu(self, proxy_user, proxy_password, proxy_port):
        # 1. install
        yield "squidインストール中...", "running"
        self.execute("apt-get update")
        self.execute("apt-get install -y squid apache2-utils")
        yield "squidインストール完了", "ok"

        # 2. squid.conf
        yield "squid.conf アップロード中...", "running"
        self.execute("cp /etc/squid/squid.conf /etc/squid/squid.conf.orig")
        conf = generate_conf(proxy_port, "ubuntu")
        self.upload(conf, "/etc/squid/squid.conf")
        yield "squid.conf アップロード完了", "ok"

        # 3. htpasswd
        yield f"htpasswd ユーザー作成中: {proxy_user}", "running"
        self.execute(f"htpasswd -cb /etc/squid/.htpasswd {proxy_user} {proxy_password}")
        yield "htpasswd ユーザー作成完了", "ok"

        # 4. firewall
        yield "ファイアウォール設定中...", "running"
        self.execute(f"ufw allow {proxy_port}/tcp")
        self.execute("ufw reload")
        yield "ファイアウォール設定完了", "ok"

        # 5. start
        yield "Squid 起動中...", "running"
        self.execute("systemctl start squid")
        yield "Squid 起動完了", "ok"

        # 6. autostart
        yield "自動起動設定中...", "running"
        self.execute("systemctl enable squid")
        yield "自動起動設定完了", "ok"
