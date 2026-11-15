from pathlib import Path


def test_dockerfile_uses_python_main():
    dockerfile_path = Path(__file__).resolve().parents[2] / "Dockerfile"
    assert dockerfile_path.exists(), f"Dockerfile not found at {dockerfile_path}"

    content = dockerfile_path.read_text(encoding="utf-8")
    assert 'CMD ["python", "main.py"]' in content


def test_nginx_conf_structure():
    root_dir = Path(__file__).resolve().parents[3]
    nginx_conf = root_dir / "deploy" / "nginx" / "nginx.conf"
    assert nginx_conf.exists(), f"nginx.conf not found at {nginx_conf}"

    content = nginx_conf.read_text(encoding="utf-8")
    assert "worker_processes auto;" in content
    assert "server_tokens off;" in content
    assert "client_max_body_size 15M;" in content
    assert "include /etc/nginx/conf.d/*.conf;" in content


def test_nginx_shopperflox_conf_routes_and_security():
    root_dir = Path(__file__).resolve().parents[3]
    conf_path = root_dir / "deploy" / "nginx" / "conf.d" / "shopperflox.conf"
    assert conf_path.exists(), f"shopperflox.conf not found at {conf_path}"

    content = conf_path.read_text(encoding="utf-8")

    # Upstream check
    assert "upstream backend_upstream" in content
    assert "server backend:8000;" in content

    # API route
    assert "location /api" in content
    assert "proxy_pass http://backend_upstream;" in content

    # Health route
    assert "location /health" in content

    # Exact metrics location with satisfy any
    assert "location = /metrics" in content
    assert "satisfy any;" in content
    assert "allow 127.0.0.1;" in content
    assert "allow ::1;" in content
    assert "allow 10.0.0.0/8;" in content
    assert "allow 172.16.0.0/12;" in content
    assert "allow 192.168.0.0/16;" in content
    assert "deny all;" in content
    assert "auth_basic" in content

    # Frontend location /
    assert "location /" in content
    assert "ShopperFlox Frontend" in content


def test_docker_compose_services():
    root_dir = Path(__file__).resolve().parents[3]
    compose_path = root_dir / "docker-compose.yml"
    assert compose_path.exists(), f"docker-compose.yml not found at {compose_path}"

    content = compose_path.read_text(encoding="utf-8")
    assert "nginx:" in content
    assert "backend:" in content
    assert "postgres:" in content
    assert "prometheus:" in content
    assert "grafana:" in content
    assert '"80:80"' in content
    assert '"127.0.0.1:5432:5432"' in content
    assert '"127.0.0.1:9090:9090"' in content
    assert '"127.0.0.1:3000:3000"' in content
    assert "--storage.tsdb.retention.time=15d" in content
    assert "pg_isready" in content
    assert "env_file:" in content
    assert "POSTGRES_USER" in content
    assert "POSTGRES_PASSWORD" in content
