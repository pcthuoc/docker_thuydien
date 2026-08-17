FROM vnoj/vnoj-base:latest

EXPOSE 8000

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "iot_monitor.asgi:application"]