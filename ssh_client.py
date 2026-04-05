import paramiko


class SSHClient:
    """WebArena VPSへのSSH接続を管理するクライアント"""

    def __init__(self):
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._connected = False

    def connect(self, host: str, port: int, user: str, password: str):
        """SSH接続を確立する"""
        self._client.connect(
            hostname=host,
            port=port,
            username=user,
            password=password,
            timeout=15,
            banner_timeout=15,
        )
        self._connected = True

    def execute(self, command: str) -> tuple[str, str, int]:
        """コマンドを実行し (stdout, stderr, exit_code) を返す"""
        if not self._connected:
            raise RuntimeError("SSH未接続")
        _stdin, stdout, stderr = self._client.exec_command(command, timeout=300)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        return out, err, exit_code

    def upload_content(self, content_str: str, remote_path: str):
        """文字列コンテンツをリモートファイルとして書き込む"""
        if not self._connected:
            raise RuntimeError("SSH未接続")
        sftp = self._client.open_sftp()
        try:
            with sftp.file(remote_path, "w") as f:
                f.write(content_str)
        finally:
            sftp.close()

    def close(self):
        """SSH接続を閉じる"""
        if self._connected:
            self._client.close()
            self._connected = False
