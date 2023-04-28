import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1
bind = "0.0.0.0:8000"
wsgi_app = "src.main:create_server()"
pidfile = "master.pid"
worker_class = "gevent"

