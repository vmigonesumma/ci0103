#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
import html
import ipaddress
import mimetypes
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

LOCAL_CA_COMMON_NAME = "host_html Local CA"


@dataclass
class TLSMaterial:
    cert_file: Path
    key_file: Path
    ca_cert_file: Path | None = None
    generated_cert: bool = False
    generated_ca: bool = False
    trusted_ca: bool = False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sirve un archivo local en una URL HTTP configurable."
    )
    parser.add_argument(
        "file",
        help="Ruta del archivo a servir, por ejemplo grafico_segmentacion_3d.html",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host a escuchar. Usa 0.0.0.0 para exponerlo en tu red local.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Puerto HTTP. Por defecto: 8000",
    )
    parser.add_argument(
        "--url-path",
        default=None,
        help=(
            "Ruta URL donde quedará disponible el archivo. "
            "Ejemplo: /grafico3d. Si no la indicas, usa el nombre del archivo."
        ),
    )
    parser.add_argument(
        "--no-root-redirect",
        action="store_true",
        help="Desactiva la redirección desde / hacia la ruta del archivo.",
    )
    parser.add_argument(
        "--https",
        action="store_true",
        help=(
            "Sirve el archivo por HTTPS. Si no indicas --cert-file y --key-file, "
            "genera certificados locales automaticamente."
        ),
    )
    parser.add_argument(
        "--cert-file",
        default=None,
        help="Ruta al certificado PEM para HTTPS.",
    )
    parser.add_argument(
        "--key-file",
        default=None,
        help="Ruta a la llave privada PEM para HTTPS.",
    )
    parser.add_argument(
        "--cert-days",
        type=int,
        default=30,
        help="Dias de validez al generar un certificado autofirmado. Por defecto: 30",
    )
    return parser


def normalize_url_path(url_path: str | None, file_path: Path) -> str:
    if not url_path:
        return f"/{file_path.name}"

    path = urlparse(url_path).path or f"/{file_path.name}"
    if not path.startswith("/"):
        path = f"/{path}"
    return path


def get_lan_ip() -> str | None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return None
    finally:
        sock.close()


def is_ip_address(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def build_subject_alt_names(host: str) -> list[str]:
    alt_names = ["DNS:localhost", "IP:127.0.0.1"]

    if host == "0.0.0.0":
        lan_ip = get_lan_ip()
        if lan_ip and lan_ip != "127.0.0.1":
            alt_names.append(f"IP:{lan_ip}")
    elif host not in {"127.0.0.1", "localhost"}:
        prefix = "IP" if is_ip_address(host) else "DNS"
        alt_names.append(f"{prefix}:{host}")

    return list(dict.fromkeys(alt_names))


def run_checked(command: list[str], error_prefix: str) -> None:
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        error_message = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise RuntimeError(f"{error_prefix}: {error_message}") from exc


def generate_local_ca(
    ca_cert_file: Path,
    ca_key_file: Path,
    days: int = 3650,
) -> None:
    if shutil.which("openssl") is None:
        raise RuntimeError(
            "OpenSSL no esta disponible. Instala OpenSSL o usa --cert-file y --key-file."
        )

    ca_cert_file.parent.mkdir(parents=True, exist_ok=True)
    run_checked(
        [
            "openssl",
            "req",
            "-x509",
            "-nodes",
            "-newkey",
            "rsa:2048",
            "-sha256",
            "-days",
            str(days),
            "-keyout",
            str(ca_key_file),
            "-out",
            str(ca_cert_file),
            "-subj",
            f"/CN={LOCAL_CA_COMMON_NAME}",
            "-addext",
            "basicConstraints=critical,CA:TRUE,pathlen:0",
            "-addext",
            "keyUsage=critical,keyCertSign,cRLSign",
            "-addext",
            "subjectKeyIdentifier=hash",
        ],
        "No pude generar la CA local",
    )
    ca_key_file.chmod(0o600)


def generate_ca_signed_cert(
    cert_file: Path,
    key_file: Path,
    ca_cert_file: Path,
    ca_key_file: Path,
    host: str,
    days: int,
) -> None:
    cert_file.parent.mkdir(parents=True, exist_ok=True)
    san_entries = ",".join(build_subject_alt_names(host))

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        csr_file = tmp_path / "server.csr"
        serial_file = tmp_path / "ca.srl"

        run_checked(
            [
                "openssl",
                "req",
                "-new",
                "-nodes",
                "-newkey",
                "rsa:2048",
                "-sha256",
                "-keyout",
                str(key_file),
                "-out",
                str(csr_file),
                "-subj",
                "/CN=localhost",
                "-addext",
                f"subjectAltName={san_entries}",
                "-addext",
                "extendedKeyUsage=serverAuth",
                "-addext",
                "keyUsage=digitalSignature,keyEncipherment",
                "-addext",
                "basicConstraints=critical,CA:FALSE",
            ],
            "No pude generar la solicitud del certificado TLS",
        )
        run_checked(
            [
                "openssl",
                "x509",
                "-req",
                "-in",
                str(csr_file),
                "-CA",
                str(ca_cert_file),
                "-CAkey",
                str(ca_key_file),
                "-CAcreateserial",
                "-CAserial",
                str(serial_file),
                "-out",
                str(cert_file),
                "-days",
                str(days),
                "-sha256",
                "-copy_extensions",
                "copyall",
            ],
            "No pude firmar el certificado TLS con la CA local",
        )

    key_file.chmod(0o600)


def trust_local_ca_on_macos(ca_cert_file: Path, marker_file: Path) -> bool:
    if sys.platform != "darwin":
        return False
    if shutil.which("security") is None:
        return False
    if marker_file.exists():
        return False

    login_keychain = Path.home() / "Library/Keychains/login.keychain-db"
    run_checked(
        [
            "security",
            "add-trusted-cert",
            "-d",
            "-r",
            "trustRoot",
            "-k",
            str(login_keychain),
            str(ca_cert_file),
        ],
        "No pude registrar la CA local en el keychain de macOS",
    )
    marker_file.parent.mkdir(parents=True, exist_ok=True)
    marker_file.write_text("trusted\n", encoding="utf-8")
    return True


def generate_self_signed_cert(
    cert_file: Path,
    key_file: Path,
    host: str,
    days: int,
) -> None:
    cert_file.parent.mkdir(parents=True, exist_ok=True)
    san_entries = ",".join(build_subject_alt_names(host))
    command = [
        "openssl",
        "req",
        "-x509",
        "-nodes",
        "-newkey",
        "rsa:2048",
        "-sha256",
        "-days",
        str(days),
        "-keyout",
        str(key_file),
        "-out",
        str(cert_file),
        "-subj",
        "/CN=localhost",
        "-addext",
        f"subjectAltName={san_entries}",
    ]

    run_checked(command, "No pude generar el certificado autofirmado")
    key_file.chmod(0o600)


def resolve_tls_files(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> TLSMaterial | None:
    https_enabled = args.https or args.cert_file or args.key_file
    if not https_enabled:
        return None

    if bool(args.cert_file) != bool(args.key_file):
        parser.error("Debes indicar ambos: --cert-file y --key-file.")

    if args.cert_days < 1:
        parser.error("--cert-days debe ser mayor o igual a 1.")

    if args.cert_file and args.key_file:
        cert_file = Path(args.cert_file).expanduser().resolve()
        key_file = Path(args.key_file).expanduser().resolve()
        if not cert_file.exists():
            parser.error(f"El certificado no existe: {cert_file}")
        if not key_file.exists():
            parser.error(f"La llave privada no existe: {key_file}")
        return TLSMaterial(cert_file=cert_file, key_file=key_file)

    cert_dir = Path(".host_html_certs").resolve()
    ca_dir = cert_dir / "ca"
    server_dir = cert_dir / "server"
    ca_cert_file = ca_dir / "host_html-local-ca-cert.pem"
    ca_key_file = ca_dir / "host_html-local-ca-key.pem"
    trust_marker = ca_dir / ".trusted-on-macos"
    cert_file = server_dir / "host_html-cert.pem"
    key_file = server_dir / "host_html-key.pem"

    generated_ca = False
    if not ca_cert_file.exists() or not ca_key_file.exists():
        generate_local_ca(ca_cert_file=ca_cert_file, ca_key_file=ca_key_file)
        generated_ca = True
        if trust_marker.exists():
            trust_marker.unlink()

    trusted_ca = trust_local_ca_on_macos(ca_cert_file, trust_marker)

    generate_ca_signed_cert(
        cert_file=cert_file,
        key_file=key_file,
        ca_cert_file=ca_cert_file,
        ca_key_file=ca_key_file,
        host=args.host,
        days=args.cert_days,
    )
    return TLSMaterial(
        cert_file=cert_file,
        key_file=key_file,
        ca_cert_file=ca_cert_file,
        generated_cert=True,
        generated_ca=generated_ca,
        trusted_ca=trusted_ca,
    )


def make_handler(
    file_path: Path,
    url_path: str,
    redirect_root: bool,
) -> type[BaseHTTPRequestHandler]:
    mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    if mime_type.startswith("text/"):
        mime_type = f"{mime_type}; charset=utf-8"

    class SingleFileHandler(BaseHTTPRequestHandler):
        served_file = file_path
        route_path = url_path
        should_redirect_root = redirect_root
        content_type = mime_type

        def do_HEAD(self) -> None:
            self._handle_request(send_body=False)

        def do_GET(self) -> None:
            self._handle_request(send_body=True)

        def log_message(self, format: str, *args: object) -> None:
            print(
                f"[{self.log_date_time_string()}] "
                f"{self.address_string()} {format % args}"
            )

        def _handle_request(self, send_body: bool) -> None:
            request_path = unquote(urlparse(self.path).path)
            alternate_path = (
                self.route_path[:-1] if self.route_path.endswith("/") else f"{self.route_path}/"
            )

            if self.should_redirect_root and request_path == "/" and self.route_path != "/":
                self.send_response(HTTPStatus.FOUND)
                self.send_header("Location", self.route_path)
                self.end_headers()
                return

            if request_path not in {self.route_path, alternate_path}:
                self._send_not_found()
                return

            body = self.served_file.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", self.content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if send_body:
                self.wfile.write(body)

        def _send_not_found(self) -> None:
            message = (
                "<h1>404</h1>"
                f"<p>Este servidor solo expone <code>{html.escape(self.route_path)}</code>.</p>"
            ).encode("utf-8")
            self.send_response(HTTPStatus.NOT_FOUND)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(message)))
            self.end_headers()
            self.wfile.write(message)

    return SingleFileHandler


def print_urls(host: str, port: int, url_path: str, scheme: str) -> None:
    local_url = f"{scheme}://127.0.0.1:{port}{url_path}"

    print(f"Archivo disponible en: {local_url}")
    if host == "0.0.0.0":
        lan_ip = get_lan_ip()
        if lan_ip:
            print(f"Tambien en tu red local: {scheme}://{lan_ip}:{port}{url_path}")
    elif host not in {"127.0.0.1", "localhost"}:
        print(f"Host configurado: {scheme}://{host}:{port}{url_path}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    file_path = Path(args.file).expanduser().resolve()
    if not file_path.exists():
        parser.error(f"El archivo no existe: {file_path}")
    if not file_path.is_file():
        parser.error(f"La ruta no es un archivo: {file_path}")

    url_path = normalize_url_path(args.url_path, file_path)
    handler = make_handler(
        file_path=file_path,
        url_path=url_path,
        redirect_root=not args.no_root_redirect,
    )

    server = ThreadingHTTPServer((args.host, args.port), handler)
    tls_files = resolve_tls_files(args, parser)
    scheme = "http"
    if tls_files is not None:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(
            certfile=str(tls_files.cert_file),
            keyfile=str(tls_files.key_file),
        )
        server.socket = context.wrap_socket(server.socket, server_side=True)
        scheme = "https"

    print(f"Sirviendo: {file_path}")
    print_urls(args.host, args.port, url_path, scheme)
    if tls_files is not None:
        print(f"Certificado: {tls_files.cert_file}")
        print(f"Llave privada: {tls_files.key_file}")
        if tls_files.ca_cert_file is not None:
            print(f"CA local: {tls_files.ca_cert_file}")
        if tls_files.generated_ca:
            print("Se genero una CA local para confiar en HTTPS dentro de tu equipo.")
        if tls_files.trusted_ca:
            print("La CA local se registro en tu keychain de macOS.")
        elif tls_files.generated_cert and tls_files.ca_cert_file is None:
            print(
                "Se genero un certificado autofirmado. "
                "El navegador mostrara advertencia hasta que confies en ese certificado."
            )
    print("Presiona Ctrl+C para detener el servidor.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
