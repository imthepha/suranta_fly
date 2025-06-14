#!/bin/bash

# Exit on error
set -e

# Create system user
sudo useradd -r -s /bin/false flightmonitor || true

# Create application directory
sudo mkdir -p /opt/flight-monitor
sudo chown flightmonitor:flightmonitor /opt/flight-monitor

# Copy application files
sudo cp -r ./* /opt/flight-monitor/
sudo cp .env /opt/flight-monitor/

# Set up Python virtual environment
cd /opt/flight-monitor
sudo -u flightmonitor python3 -m venv venv
sudo -u flightmonitor venv/bin/pip install -r requirements.txt

# Copy service files
sudo cp flight-monitor.service /etc/systemd/system/
sudo cp flight-monitor-celery.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start services
sudo systemctl enable flight-monitor
sudo systemctl enable flight-monitor-celery
sudo systemctl start flight-monitor
sudo systemctl start flight-monitor-celery

echo "Deployment completed successfully!"
echo "Check service status with:"
echo "sudo systemctl status flight-monitor"
echo "sudo systemctl status flight-monitor-celery" 